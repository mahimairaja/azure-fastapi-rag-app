from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.security import get_password_hash, verify_password, create_access_token
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_id: int
    username: str
    role: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None


router = APIRouter(tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """To register a new user."""
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"message": "User created successfully", "user_id": db_user.id}

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """To generate an access token for a user."""
    # Find the user by username
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Check if user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30) 
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "username": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "expires_in": 1800, 
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }

@router.post("/validate-token")
def validate_token(token: str):
    """To validate a token and return user information."""
    from app.services.security import decode_token
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    if "exp" in payload and payload["exp"] < datetime.utcnow().timestamp():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    return {
        "valid": True, 
        "user_id": payload.get("sub"),
        "role": payload.get("role"),
        "username": payload.get("username")
    } 