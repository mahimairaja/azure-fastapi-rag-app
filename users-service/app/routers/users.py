from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.user import User
from app.services.authorization import authorization_middleware

# Data models
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    
    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    username: str = None
    email: EmailStr = None
    role: str = None

class UserCreate(UserBase):
    """Model for creating a user from the auth service info."""
    pass

# Create router
router = APIRouter(tags=["Users"])

# Sync a user from auth service to users service
@router.post("/sync", response_model=UserResponse)
async def sync_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """
    Sync a user from the auth service to the users service.
    This is called when a user is created in the auth service.
    """
    # Only admin can sync users
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can sync users"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        # Update user data
        existing_user.email = user_data.email
        existing_user.role = user_data.role
        db.commit()
        db.refresh(existing_user)
        return existing_user
    
    # Create new user
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        role=user_data.role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

# Get all users (admin only)
@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """Get all users. Requires admin role."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

# Get user by ID (admin or own user)
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """Get a user by ID. Users can only access their own data, admins can access any user."""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # If not admin and not the same user, deny access
    if current_user.get("role") != "admin" and str(current_user.get("user_id")) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user data"
        )
    
    return user

# Update user (admin or own user)
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """Update a user. Users can only update their own data, admins can update any user."""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # If not admin and not the same user, deny access
    if current_user.get("role") != "admin" and str(current_user.get("user_id")) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    # Only admins can update roles
    if user_data.role and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update roles"
        )
    
    # Update user data
    if user_data.username:
        user.username = user_data.username
    if user_data.email:
        user.email = user_data.email
    if user_data.role and current_user.get("role") == "admin":
        user.role = user_data.role
    
    db.commit()
    db.refresh(user)
    
    return user

# Delete user (admin only)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authorization_middleware)
):
    """Delete a user. Requires admin role."""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Only admins can delete users
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )
    
    db.delete(user)
    db.commit()
    
    return None 