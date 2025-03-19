from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from app.database import init_db
from app.routers import rag


security_scheme = HTTPBearer(
    description="Enter 'Bearer' followed by a space and your JWT token",
    auto_error=False
)


app = FastAPI(
    title="RAG Microservice",
    description="Retrieval-Augmented Generation service for documents",
    version="1.0.0",
    root_path="/api/rag",
    docs_url="/docs",  
    redoc_url="/redoc"  
)

app.openapi_schema = None 

original_openapi = app.openapi


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = original_openapi()
    
    # Add security scheme components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your JWT token in the format: Bearer YOUR_TOKEN",
    }
    
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(rag.router)


os.makedirs("storage/documents", exist_ok=True)
os.makedirs("storage/embeddings", exist_ok=True)


@app.on_event("startup")
def startup_db_client():
    init_db()


@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Welcome to the RAG (Retrieval-Augmented Generation) Microservice API",
        "service_name": "rag-service",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "rag-service"} 