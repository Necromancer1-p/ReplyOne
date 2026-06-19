import os
import datetime
import logging
import jwt
import bcrypt

logger = logging.getLogger("replyone.security")

# Secret keys from environment
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkeythatisreallylongandsecure12345!")
JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    logger.debug("Hashing password directly using bcrypt...")
    try:
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        logger.debug("Password hashed successfully.")
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}", exc_info=True)
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    logger.debug("Verifying password directly using bcrypt...")
    try:
        pwd_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        match = bcrypt.checkpw(pwd_bytes, hash_bytes)
        logger.debug(f"Password verification result: {match}")
        return match
    except Exception as e:
        logger.error(f"Error verifying password: {e}", exc_info=True)
        return False

def create_access_token(user_id: int, tenant_id: int, role: str, expires_delta: datetime.timedelta | None = None) -> str:
    logger.info(f"Generating access token for user {user_id}, tenant {tenant_id}, role {role}")
    try:
        if expires_delta:
            expire = datetime.datetime.utcnow() + expires_delta
        else:
            expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
            
        payload = {
            "sub": str(user_id),
            "tid": tenant_id,
            "role": role,
            "exp": expire,
            "iat": datetime.datetime.utcnow()
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.info(f"Access token successfully created for user {user_id}")
        return token
    except Exception as e:
        logger.error(f"Error creating access token: {e}", exc_info=True)
        raise

def verify_access_token(token: str) -> dict | None:
    logger.debug("Verifying access token...")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        logger.debug(f"Access token verified. Sub={payload.get('sub')}, Tenant={payload.get('tid')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Access token has expired.")
        return None
    except jwt.PyJWTError as e:
        logger.error(f"Access token validation failed: {e}")
        return None
