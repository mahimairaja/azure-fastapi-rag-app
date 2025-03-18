import casbin
import os
from fastapi import Request, HTTPException, status, Depends
from app.services.auth_client import AuthClient
from typing import Dict, Any

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
p, admin, /users, POST
p, admin, /users, PUT
p, admin, /users, DELETE
p, user, /users, GET
p, user, /users/{id}, GET
g, admin, user""")

enforcer = casbin.Enforcer(model_path, policy_path)

def check_permission(user_role: str, path: str, method: str) -> bool:
    """
    Check if the user has permission to access the given path with the given method.
    """
    # Convert the HTTP method to uppercase to match policy
    method = method.upper()
    
    # Check if the user has the required permission
    return enforcer.enforce(user_role, path, method)

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
    
    if not check_permission(user_role, path, method):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource."
        )
    
    return user_info 