from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import auth


app = FastAPI(
    title="Auth Microservice",
    description="Authentication service with JWT token management",
    version="1.0.0",
    root_path="/api/auth"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production to restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/auth")


@app.on_event("startup")
def startup_db_client():
    init_db()


@app.get("/", tags=["Root"])
def read_root(request: Request):
    root_path = str(request.scope.get("root_path"))
    return {
        "message": f"Welcome to the Auth Microservice API - {root_path}",
        "service_name": "auth-service",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "auth-service"} 
