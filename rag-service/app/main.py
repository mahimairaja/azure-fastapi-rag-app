from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.database import init_db
from app.routers import rag

# Initialize the FastAPI app
app = FastAPI(
    title="RAG Microservice",
    description="Retrieval-Augmented Generation service for documents",
    version="1.0.0",
    root_path="/api/rag"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production to restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rag.router, prefix="/rag")

# Create storage directories if they don't exist
os.makedirs("storage/documents", exist_ok=True)
os.makedirs("storage/embeddings", exist_ok=True)

# Initialize database on startup
@app.on_event("startup")
def startup_db_client():
    init_db()

# Root endpoint
@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Welcome to the RAG (Retrieval-Augmented Generation) Microservice API",
        "service_name": "rag-service",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "rag-service"} 