from typing import List, Dict, Any, Optional
import os
import uuid
from datetime import datetime
import json
import tempfile
from sqlalchemy.orm import Session
from app.models.document import Document

# Add imports for LangChain, Hugging Face, and Groq - updated to use community packages
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import logging

# Load environment variables and setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Hugging Face embeddings
try:
    EMBEDDINGS = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    logger.info("HuggingFace Embeddings initialized successfully.")
except ImportError as e:
    logger.error(f"Error initializing HuggingFace Embeddings: {e}")
    logger.warning("Using fallback mode without vector embeddings.")
    EMBEDDINGS = None

# Configure document store paths
DOCUMENT_STORE_PATH = os.environ.get("DOCUMENT_STORE_PATH", "storage/documents")
CHROMA_PERSIST_DIRECTORY = os.path.join(DOCUMENT_STORE_PATH, "chroma_db")

os.makedirs(DOCUMENT_STORE_PATH, exist_ok=True)
os.makedirs(CHROMA_PERSIST_DIRECTORY, exist_ok=True)

# Initialize vector store if embeddings are available
vector_store = None
if EMBEDDINGS is not None:
    try:
        vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIRECTORY,
            embedding_function=EMBEDDINGS
        )
        logger.info("Vector store initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing vector store: {e}")
        vector_store = None

# Configure text splitter for chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

# Initialize Groq LLM if API key is available
groq_api_key = os.getenv("GROQ_API_KEY")
llm = None
if groq_api_key:
    try:
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192",
            temperature=0.1,
            max_tokens=1024
        )
        logger.info("Groq API initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Groq API: {e}")
else:
    logger.warning("GROQ_API_KEY not found in environment variables. Answer generation will be limited.")

# Simple prompt template for the RAG
qa_template = """
You are a helpful AI assistant that answers questions based on the provided context.
If you don't know the answer based on the context, just say that you don't know.
Don't try to make up an answer.

Context:
{context}

Question: {question}

Answer:
"""

QA_PROMPT = PromptTemplate(
    template=qa_template,
    input_variables=["context", "question"]
)

class RAGService:
    """Service for Retrieval-Augmented Generation functionality."""
    
    def __init__(self):
        # Storage for documents and embeddings
        self.storage_dir = DOCUMENT_STORE_PATH
        self.embeddings_dir = "storage/embeddings"
        
        # Create storage directories if they don't exist
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.embeddings_dir, exist_ok=True)
    
    def process_document(self, content: str, metadata: Dict[str, Any], db: Session) -> str:
        """
        Process a document and store its content and metadata.
        This includes:
        1. Chunking the document
        2. Embedding the chunks
        3. Storing the embeddings in the vector database
        """
        # Generate a unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Store document in the database
        db_document = Document(
            doc_id=doc_id,
            title=metadata.get("title", "Untitled Document"),
            content=content,
            doc_metadata=metadata
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Save document to disk as a backup
        self._save_document(doc_id, content, metadata)
        
        # Process with LangChain if vector store is available
        if vector_store is not None:
            try:
                # Save content to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
                    temp_file.write(content.encode('utf-8'))
                    temp_file_path = temp_file.name
                
                # Load and split the document
                loader = TextLoader(temp_file_path)
                documents = loader.load()
                splits = text_splitter.split_documents(documents)
                
                # Add document chunks to vector store with the document ID as the collection
                vector_store.add_documents(
                    splits,
                    collection_name=doc_id
                )
                vector_store.persist()
                
                logger.info(f"Document {doc_id} processed and added to vector store with {len(splits)} chunks.")
                
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
            except Exception as e:
                logger.error(f"Error processing document: {e}")
        else:
            logger.warning("Vector store not available. Document will not be processed for semantic search.")
        
        return doc_id
    
    def query(self, query_text: str, top_k: int = 3, db: Session = None) -> List[Dict[str, Any]]:
        """
        Query the documents using the provided text.
        Returns top_k most relevant documents.
        
        This function:
        1. Generates an embedding for the query
        2. Performs a similarity search in the vector database
        3. Returns the most relevant chunks
        """
        # Try vector-based retrieval if available
        if vector_store is not None:
            try:
                retriever = vector_store.as_retriever(
                    search_kwargs={"k": top_k}
                )
                docs = retriever.get_relevant_documents(query_text)
                
                if docs:
                    answer = self._generate_answer(query_text, docs)
                    results = []
                    
                    for doc in docs:
                        collection_name = doc.metadata.get("collection_name", "")
                        if db and collection_name:
                            document = db.query(Document).filter(Document.doc_id == collection_name).first()
                            if document:
                                results.append({
                                    "id": document.doc_id,
                                    "title": document.title,
                                    "content": doc.page_content,  # Return the chunk content from the vector DB
                                    "doc_metadata": document.doc_metadata,
                                    "created_at": document.created_at.isoformat() if document.created_at else None,
                                    "answer": answer
                                })
                    
                    # If we found vector results, return them
                    if results:
                        return results
            except Exception as e:
                logger.error(f"Error during vector search: {e}")
        
        # Fallback to database retrieval
        if db:
            documents = db.query(Document).order_by(Document.created_at.desc()).limit(top_k).all()
            
            results = []
            for doc in documents:
                results.append({
                    "id": doc.doc_id,
                    "title": doc.title,
                    "content": doc.content,
                    "doc_metadata": doc.doc_metadata,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                })
                
            return results
        
        # Final fallback to file-based retrieval
        return self._get_documents_from_files(top_k)
    
    def _generate_answer(self, query: str, retrieved_docs) -> str:
        """
        Generate an answer to the query based on retrieved documents using Groq API.
        """
        if not retrieved_docs:
            return "No relevant information found to answer your question."
        
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
        if llm is not None:
            try:
                formatted_prompt = QA_PROMPT.format(context=context, question=query)
                response = llm.invoke(formatted_prompt)
                return response.content
            except Exception as e:
                logger.error(f"Error generating answer with Groq: {e}")
                return f"Based on the retrieved information, here's what I found: {context[:500]}..."
        else:
            return f"Based on the retrieved information, here's what I found: {context[:500]}..."
    
    def get_document(self, doc_id: str, db: Session = None) -> Optional[Dict[str, Any]]:
        """Get a document by its ID."""
        if db:
            doc = db.query(Document).filter(Document.doc_id == doc_id).first()
            if doc:
                return {
                    "id": doc.doc_id,
                    "title": doc.title,
                    "content": doc.content,
                    "doc_metadata": doc.doc_metadata,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                }
        
        # Fallback to file-based retrieval
        return self._load_document(doc_id)
    
    def delete_document(self, doc_id: str, db: Session = None) -> bool:
        """Delete a document by its ID."""
        deleted = False
        
        if db:
            doc = db.query(Document).filter(Document.doc_id == doc_id).first()
            if doc:
                db.delete(doc)
                db.commit()
                deleted = True
        
        # Also delete from filesystem if it exists
        doc_path = os.path.join(self.storage_dir, f"{doc_id}.json")
        if os.path.exists(doc_path):
            os.remove(doc_path)
            deleted = True
        
        # Delete from vector store if available
        if vector_store is not None:
            try:
                vector_store.delete_collection(doc_id)
                vector_store.persist()
                logger.info(f"Deleted document {doc_id} from vector store")
            except Exception as e:
                logger.error(f"Error deleting document from vector store: {e}")
            
        return deleted
    
    def _save_document(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        """Save a document to disk."""
        document = {
            "id": doc_id,
            "content": content,
            "metadata": metadata,  # Keep as metadata in the file for backward compatibility
            "created_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(self.storage_dir, f"{doc_id}.json"), "w") as f:
            json.dump(document, f)
    
    def _load_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Load a document from disk."""
        doc_path = os.path.join(self.storage_dir, f"{doc_id}.json")
        if not os.path.exists(doc_path):
            return None
            
        try:
            with open(doc_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading document {doc_id}: {e}")
            return None
    
    def _get_documents_from_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get documents from files, sorted by creation time."""
        if not os.path.exists(self.storage_dir):
            return []
            
        documents = []
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                doc_path = os.path.join(self.storage_dir, filename)
                try:
                    with open(doc_path, "r") as f:
                        document = json.load(f)
                        documents.append(document)
                except Exception as e:
                    print(f"Error loading document {filename}: {e}")
        
        # Sort by creation time (newest first)
        documents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return documents[:limit]

# Create a singleton instance
rag_service = RAGService() 