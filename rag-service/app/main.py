from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from app.database import init_db
from app.routers import rag

# Security scheme
security_scheme = HTTPBearer(
    description="Enter 'Bearer' followed by a space and your JWT token",
    auto_error=False
)

# Initialize the FastAPI app
app = FastAPI(
    title="RAG Microservice",
    description="Retrieval-Augmented Generation service for documents",
    version="1.0.0",
    root_path="/api/rag",
    docs_url="/docs",  # This will be accessible at /api/rag/docs
    redoc_url="/redoc"  # This will be accessible at /api/rag/redoc
)

# Add security scheme to OpenAPI
app.openapi_schema = None  # Reset to ensure it gets regenerated

# Original openapi method
original_openapi = app.openapi

# Define a new function that adds security schemes
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = original_openapi()
    
    # Add security scheme components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    
    # Add Bearer Authentication security scheme
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your JWT token in the format: Bearer YOUR_TOKEN",
    }
    
    # Add security requirement for all endpoints
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Replace openapi function
app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production to restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - remove the prefix as it's defined in the router
app.include_router(rag.router)

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