import logging
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db, tenant_context
from app.core.security import verify_access_token
from app.models.models import User, Tenant

logger = logging.getLogger("replyone.deps")

security_bearer = HTTPBearer(auto_error=False)

async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer)
) -> dict:
    """Extract and verify token payload."""
    if not credentials:
        logger.warning("Missing Authorization header credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Missing Authorization header.",
        )
    
    token = credentials.credentials
    payload = verify_access_token(token)
    if not payload:
        logger.warning("Invalid or expired token credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token.",
        )
        
    return payload

async def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Fetch user from database and verify tenant context."""
    user_id = int(payload.get("sub"))
    tenant_id = int(payload.get("tid"))
    
    logger.debug(f"Fetching user {user_id} and setting tenant context to {tenant_id}")
    
    # Enforce tenant isolation in ContextVar
    tenant_context.set(tenant_id)
    
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalars().first()
    
    if not user:
        logger.error(f"User {user_id} not found under tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
        
    if not user.is_active:
        logger.warning(f"Inactive user {user_id} tried to log in")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
        
    return user

def require_role(allowed_roles: list[str]):
    """RBAC Dependency to enforce route-level roles."""
    async def role_checker(user: User = Depends(get_current_user)):
        logger.debug(f"Checking role for user {user.email}. User role: {user.role}, Allowed: {allowed_roles}")
        if user.role not in allowed_roles:
            logger.warning(f"Role violation. User {user.email} with role {user.role} tried accessing role-protected route (requires {allowed_roles})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return user
    return role_checker
