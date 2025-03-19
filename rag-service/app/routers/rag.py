from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging
from datetime import datetime
from app.database import get_db
from app.models.document import Document
from app.services.authorization import authorization_middleware
from app.services.rag_service import process_document, query_documents

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(prefix="/rag", tags=["RAG"])

# Define Pydantic models
class DocumentResponse(BaseModel):
    id: int = Field(..., description="Numeric ID of the document")
    doc_id: str = Field(..., description="UUID string of the document")
    title: str
    content: Optional[str] = None
    doc_metadata: Dict[str, Any]
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SourceResponse(BaseModel):
    content: str
    metadata: Dict[str, Any]

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceResponse]
    num_results: int

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    Upload and process a document for RAG.
    Only admin and editor roles can upload documents.
    """
    # Check if user is admin or editor
    user_role = current_user.get("role", "")
    if user_role not in ["admin", "editor"]:
        logger.error(f"User {current_user.get('username')} not authorized to upload documents")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and editor roles can upload documents"
        )
    
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ["pdf", "txt"]:
        logger.error(f"Unsupported file type: {file_extension}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF and TXT files are supported."
        )
    
    content = await file.read()
    
    metadata = {
        "title": title,
        "description": description,
        "filename": file.filename,
        "content_type": file.content_type,
        "uploader_id": current_user.get("user_id"),
        "uploader_username": current_user.get("username")
    }
    
    try:
        doc_metadata = await process_document(
            content=content,
            filename=file.filename,
            title=title,
            description=description
        )
        
        import uuid
        doc_id = str(uuid.uuid4())
        
        db_document = Document(
            doc_id=doc_id,
            title=title,
            content=content.decode("utf-8", errors="replace"),
            doc_metadata={
                **doc_metadata,
                "uploader_id": current_user.get("user_id"),
                "uploader_username": current_user.get("username")
            }
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        logger.info(f"Document {title} uploaded successfully by user {current_user.get('username')}")
        return db_document
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0, 
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    List all accessible documents.
    Admin can see all documents, other users see only their own.
    """
    user_role = current_user.get("role", "")
    user_id = current_user.get("user_id")
    
    if user_role == "admin":
        # Admin can see all documents
        documents = db.query(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    else:
        # Other roles can only see documents they uploaded
        documents = db.query(Document).filter(
            Document.doc_metadata['uploader_id'].astext == str(user_id)
        ).order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    logger.info(f"Listed {len(documents)} documents for user {current_user.get('username')}")
    return documents

@router.post("/query", response_model=QueryResponse)
async def query_rag(
    query_data: QueryRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    Query documents using RAG.
    All authenticated users can query documents.
    """
    try:
        query_result = await query_documents(
            query=query_data.query,
            top_k=query_data.top_k
        )
        
        answer = query_result.get("answer", "")
        
        if not answer:
            answer = "No specific answer was found for your query in the available documents."
        
        sources = []
        for source in query_result.get("sources", []):
            doc_id = None
            collection_name = source.get("metadata", {}).get("collection_name", "")
            
            if collection_name and db:
                docs = db.query(Document).all()
                for doc in docs:
                    if doc.doc_metadata and isinstance(doc.doc_metadata, dict):
                        if doc.doc_metadata.get("collection_name") == collection_name:
                            doc_id = doc.doc_id
                            break
            
            source_response = {
                "content": source.get("content", ""),
                "metadata": {
                    "id": doc_id or "unknown",
                    "title": source.get("metadata", {}).get("source", "Unknown Document"),
                    "doc_metadata": source.get("metadata", {})
                }
            }
            sources.append(source_response)
        
        response = {
            "query": query_data.query,
            "answer": answer,
            "sources": sources,
            "num_results": len(sources)
        }
        
        logger.info(f"Query '{query_data.query}' executed by user {current_user.get('username')}")
        return response
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying documents: {str(e)}"
        ) 