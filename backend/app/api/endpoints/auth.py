import logging
import re
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db, DATABASE_URL
from app.models.models import Tenant, User, ShopSettings, Subscription
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, MessageResponse
from app.core.security import hash_password, verify_password, create_access_token

logger = logging.getLogger("replyone.api.auth")
router = APIRouter()

def slugify(text: str) -> str:
    """Simple slugify helper."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    logger.info(f"Registration request started for email: {req.email}, business: {req.business_name}")
    
    try:
        # Check if email already exists globally (users.email is unique globally)
        logger.debug(f"Checking if user email {req.email} already exists...")
        result = await db.execute(select(User).where(User.email == req.email))
        existing_user = result.scalars().first()
        if existing_user:
            logger.warning(f"Registration failed: email {req.email} already exists.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists."
            )

        # Generate unique slug for tenant
        base_slug = slugify(req.business_name)
        slug = base_slug
        counter = 1
        logger.debug(f"Generating unique slug. Base slug: {base_slug}")
        
        while True:
            slug_check = await db.execute(select(Tenant).where(Tenant.slug == slug))
            if not slug_check.scalars().first():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        logger.debug(f"Unique slug determined: {slug}")

        # Create Tenant
        tenant = Tenant(
            name=req.business_name,
            slug=slug,
            plan="trial",
            onboarding_complete=False
        )
        db.add(tenant)
        await db.flush() # Flush to get tenant.id
        logger.info(f"Tenant created with ID: {tenant.id}, Slug: {slug}")

        # Create User (Owner)
        hashed_pwd = hash_password(req.password)
        user = User(
            tenant_id=tenant.id,
            email=req.email,
            password_hash=hashed_pwd,
            role="owner",
            is_active=True
        )
        db.add(user)
        await db.flush() # Flush to get user.id
        logger.info(f"Owner user created with ID: {user.id} for tenant: {tenant.id}")

        # Create ShopSettings (1:1 with tenant)
        shop_settings = ShopSettings(
            tenant_id=tenant.id,
            ai_tone="balanced",
            ai_auto_reply_enabled=True,
            ai_confidence_threshold=0.700
        )
        db.add(shop_settings)

        # Create Subscription
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_tier="free",
            status="trialing",
            messages_used_this_period=0,
            message_quota=500
        )
        db.add(subscription)
        
        # Commit transaction
        await db.commit()
        logger.info(f"Registration fully committed for tenant {tenant.id} and user {user.id}")

        # Create access token
        access_token = create_access_token(user_id=user.id, tenant_id=tenant.id, role=user.role)
        
        # In a real environment, set HttpOnly refresh token cookie. 
        # We can simulate this by setting a mock cookie.
        is_secure = not DATABASE_URL.startswith("sqlite")
        response.set_cookie(
            key="refresh_token",
            value="mock_refresh_token_value",
            httponly=True,
            secure=is_secure,
            samesite="lax" if not is_secure else "strict",
            max_age=30 * 24 * 3600
        )
        logger.debug("HttpOnly refresh token cookie set.")
        
        return TokenResponse(
            access_token=access_token,
            role=user.role,
            tenant_id=tenant.id,
            onboarding_complete=tenant.onboarding_complete
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error occurred: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong. Please try again."
        )

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    logger.info(f"Login request started for email: {req.email}")
    
    try:
        # Check user
        result = await db.execute(select(User).where(User.email == req.email))
        user = result.scalars().first()
        
        if not user:
            logger.warning(f"Login failed: User with email {req.email} not found.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password."
            )
            
        logger.debug(f"User {req.email} found. Checking password...")
        if not verify_password(req.password, user.password_hash):
            logger.warning(f"Login failed: Incorrect password for user {req.email}.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password."
            )
            
        if not user.is_active:
            logger.warning(f"Login failed: User {req.email} is inactive.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated."
            )

        # Get tenant to check onboarding state
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = tenant_result.scalars().first()
        
        logger.info(f"User {user.id} logged in successfully under tenant {user.tenant_id}")
        
        # Generate token
        access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
        
        # Set refresh token cookie
        is_secure = not DATABASE_URL.startswith("sqlite")
        response.set_cookie(
            key="refresh_token",
            value="mock_refresh_token_value",
            httponly=True,
            secure=is_secure,
            samesite="lax" if not is_secure else "strict",
            max_age=30 * 24 * 3600
        )
        
        return TokenResponse(
            access_token=access_token,
            role=user.role,
            tenant_id=user.tenant_id,
            onboarding_complete=tenant.onboarding_complete if tenant else False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error occurred: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong. Please try again."
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    logger.info("Token refresh requested.")
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        logger.warning("Refresh token cookie missing.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again."
        )
        
    # In a real app we would verify refresh_token_hash in database.
    # For this local mock, we assume the cookie is valid and we refresh the token.
    # We will search for a default owner user to generate the token for.
    logger.debug("Validating mock refresh token...")
    result = await db.execute(select(User).limit(1))
    user = result.scalars().first()
    if not user:
        logger.error("No user exists to refresh token for.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )
        
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalars().first()
    
    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    logger.info(f"Token refreshed successfully for user {user.id}")
    
    return TokenResponse(
        access_token=access_token,
        role=user.role,
        tenant_id=user.tenant_id,
        onboarding_complete=tenant.onboarding_complete if tenant else False
    )

@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    logger.info("Logout requested. Clearing refresh token cookie.")
    response.delete_cookie("refresh_token")
    return MessageResponse(message="You have been logged out")
