import casbin
import os
from fastapi import Request, HTTPException, status, Depends
from app.services.auth_client import AuthClient
from typing import Dict, Any
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the enforcer
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rbac_model.conf")
policy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rbac_policy.csv")

# Create the directory for the model and policy if it doesn't exist
os.makedirs(os.path.dirname(model_path), exist_ok=True)

# Write the model and policy files if they don't exist
if not os.path.exists(model_path):
    with open(model_path, "w") as f:
        f.write("""[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act""")

if not os.path.exists(policy_path):
    with open(policy_path, "w") as f:
        f.write("""p, admin, /users, GET
p, admin, /users/, GET
p, admin, /users, POST
p, admin, /users, PUT
p, admin, /users, DELETE
p, user, /users/me, GET
p, user, /users/{id}, GET
p, admin, /users/{id}, GET
p, admin, /users/sync, POST
p, admin, /users/{id}/role, PUT
g, admin, user""")

enforcer = casbin.Enforcer(model_path, policy_path)

def check_permission(user_role: str, path: str, method: str) -> bool:
    """
    Check if the user has permission to access the given path with the given method.
    """
    # Convert the HTTP method to uppercase to match policy
    method = method.upper()
    
    # Normalize the path to match the policy rules
    # Remove /api/users prefix to get just /users or /users/{id}
    normalized_path = path
    if path.startswith("/api/users"):
        normalized_path = path.replace("/api/users", "")
    
    # Fix empty path to be root
    if not normalized_path:
        normalized_path = "/"
    
    # Handle trailing slashes consistently
    if normalized_path != "/" and normalized_path.endswith("/"):
        # Also try without the trailing slash
        if enforcer.enforce(user_role, normalized_path[:-1], method):
            return True
    
    # Try matching with the ID parameter for paths like /users/1
    if "/users/" in normalized_path and normalized_path.count("/") == 2:
        parts = normalized_path.split("/")
        if len(parts) == 3 and parts[1] == "users" and parts[2].isdigit():
            parameterized_path = "/users/{id}"
            if enforcer.enforce(user_role, parameterized_path, method):
                return True
    
    # Log for debugging
    logger.info(f"Checking permission: role={user_role}, path={normalized_path}, method={method}")
    
    # Check if the user has the required permission
    return enforcer.enforce(user_role, normalized_path, method)

async def authorization_middleware(
    request: Request,
    user_info: Dict[str, Any] = Depends(AuthClient.get_current_user)
):
    """
    FastAPI middleware for authorization using Casbin.
    """
    path = request.url.path
    method = request.method
    
    # Get the user's role from the validated token
    user_role = user_info.get("role", "anonymous")
    
    # Log the request for debugging
    logger.info(f"Authorization request: role={user_role}, path={path}, method={method}")
    
    if not check_permission(user_role, path, method):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource."
        )
    
    return user_info 