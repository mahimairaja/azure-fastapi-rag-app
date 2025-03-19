import requests
import os
from fastapi import HTTPException, status, Request
from typing import Dict, Any, Optional

# Auth service URL (environment variable in production)
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")

class AuthClient:
    """Client for communicating with the Auth microservice."""
    
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """
        Validate a JWT token with the Auth service.
        Returns user info if valid, raises exception if not.
        """
        try:
            response = requests.post(
                f"{AUTH_SERVICE_URL}/api/auth/auth/validate-token?token={token}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Handle different error responses
                error_detail = "Authentication failed"
                if response.status_code == 401:
                    error_detail = "Invalid or expired token"
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_detail,
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        except requests.RequestException as e:
            # Handle connection errors to auth service
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Authentication service unavailable: {str(e)}"
            )
    
    @staticmethod
    def get_token_from_request(request: Request) -> Optional[str]:
        """Extract the JWT token from the Authorization header."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        return auth_header.split(" ")[1]
    
    @staticmethod
    async def get_current_user(request: Request):
        """
        Dependency for getting the current authenticated user.
        Uses the token from the request.
        """
        token = AuthClient.get_token_from_request(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate token and get user info
        return AuthClient.validate_token(token) 