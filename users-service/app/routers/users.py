from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from app.database import get_db
from app.models.user import User
from app.services.authorization import authorization_middleware
from pydantic import BaseModel, EmailStr, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: Optional[str] = None

class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="User role (e.g., 'admin', 'user', 'moderator')")

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    role: str = "user"  # Default role is "user"

# Get current user profile
@router.get("/me", response_model=UserResponse)
async def read_users_me(
    db: Session = Depends(get_db),
    current_user = Depends(authorization_middleware)
):
    """
    To get current user profile.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(f"User {user.username} retrieved their own profile")
    return user

# Get user by ID
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(authorization_middleware)
):
    """
    Get a specific user by ID.
    Users can only view their own profile, while admins can view any profile.
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions
    if current_user.get("role") != "admin" and str(current_user.get("user_id")) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user data"
        )
    
    logger.info(f"User {user_id} profile accessed by {current_user.get('username')}")
    return user

# List all users (admin only)
@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(authorization_middleware)
):
    """
    To list all users. Requires admin role.
    """
    # Only admins can list all users
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can list all users"
        )
    
    users = db.query(User).offset(skip).limit(limit).all()
    logger.info(f"Listed {len(users)} users successfully by admin {current_user.get('username')}")
    return users

# Update user role (admin only)
@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(authorization_middleware)
):
    """
    Update a user's role. Admin only.
    """
    # Only admins can update roles
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update roles"
        )
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update role
    user.role = role_update.role
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user.username} role updated to {role_update.role} by admin {current_user.get('username')}")
    return user

# Update user profile
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(authorization_middleware)
):
    """
    Update a user profile.
    Users can only update their own profile, while admins can update any profile.
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions
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
    
    logger.info(f"User {user.username} profile updated")
    return user

# Delete user (admin only)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(authorization_middleware)
):
    """
    Delete a user. Admin only.
    """
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
    
    logger.info(f"User {user.username} deleted by admin {current_user.get('username')}")
    return None

# Sync user from auth service (admin only)
@router.post("/sync", response_model=UserResponse)
async def sync_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user = Depends(authorization_middleware)
):
    """
    Sync a user from the auth service to the users service.
    This is called when a user is created in the auth service.
    Admin only.
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
        logger.info(f"User {existing_user.username} synchronized (updated)")
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
    
    logger.info(f"User {db_user.username} synchronized (created)")
    return db_user 
