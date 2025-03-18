from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, File, UploadFile
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.document import Document
from app.services.authorization import authorization_middleware
from app.services.rag_service import rag_service

# Define request and response models
class DocumentResponse(BaseModel):
    id: str
    title: str
    content: str
    doc_metadata: Dict[str, Any]
    created_at: Optional[str] = None
    
    class Config:
        orm_mode = True

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

# Create router
router = APIRouter(tags=["RAG"])

@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    Upload and process a document.
    Only admin and editor roles can upload documents.
    """
    # Check if user is admin or editor
    user_role = current_user.get("role", "")
    if user_role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and editor roles can upload documents"
        )
    
    # Read file content
    content = await file.read()
    content_str = content.decode("utf-8", errors="replace")
    
    # Create metadata
    metadata = {
        "title": title,
        "description": description,
        "filename": file.filename,
        "content_type": file.content_type,
        "uploader_id": current_user.get("user_id"),
        "uploader_username": current_user.get("username")
    }
    
    # Process document
    doc_id = rag_service.process_document(content_str, metadata, db)
    
    return {"message": "Document processed successfully", "document_id": doc_id}

@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    Get a list of documents.
    All authenticated users can access this endpoint.
    """
    documents = db.query(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    return documents

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    Get a document by ID.
    All authenticated users can access this endpoint.
    """
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document

@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    Delete a document by ID.
    Only admin role can delete documents.
    """
    # Only admins can delete documents
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete documents"
        )
    
    document = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    success = rag_service.delete_document(doc_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
    
    return None

@router.post("/query", response_model=List[DocumentResponse])
async def query_documents(
    query_data: QueryRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    Query documents with a text search.
    All authenticated users can access this endpoint.
    """
    results = rag_service.query(query_data.query, query_data.top_k, db)
    
    return results 