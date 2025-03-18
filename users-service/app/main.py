from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.database import init_db
from app.routers import users

# Initialize the FastAPI app
app = FastAPI(
    title="Users Microservice",
    description="User management service with Casbin RBAC",
    version="1.0.0",
    root_path="/api/users"
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
app.include_router(users.router, prefix="/users")

# Initialize database on startup
@app.on_event("startup")
def startup_db_client():
    init_db()

# Root endpoint
@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Welcome to the User Management Microservice API",
        "service_name": "users-service",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "users-service"} 