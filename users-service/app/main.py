from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.models import SecurityScheme
import os
from app.database import init_db
from app.routers import users

security_scheme = HTTPBearer(
    description="Enter 'Bearer' followed by a space and your JWT token",
    auto_error=False
)

app = FastAPI(
    title="Users Microservice",
    description="User management service with Casbin RBAC",
    version="1.0.0",
    root_path="/api/users",
    docs_url="/docs",  
    redoc_url="/redoc"  
)

app.openapi_schema = None  

original_openapi = app.openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = original_openapi()
    
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
    allow_origins=["*"],  # Change in production to restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)

@app.on_event("startup")
def startup_db_client():
    init_db()


@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Welcome to the User Management Microservice API",
        "service_name": "users-service",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "users-service"} 