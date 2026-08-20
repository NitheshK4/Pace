import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union, Tuple
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def generate_project_api_key() -> Tuple[str, str, str]:
    """
    Generates a new Pace project ingestion key.
    Returns: (raw_key, key_hash, key_prefix)
    - raw_key: 'pace_...' (shown ONCE to user, never saved)
    - key_hash: HMAC-SHA256 salted hash stored in database
    - key_prefix: first 12 characters 'pace_abc12345' stored for identification
    """
    random_bytes = secrets.token_urlsafe(32)
    raw_key = f"pace_{random_bytes}"
    key_prefix = raw_key[:12]
    key_hash = hash_project_api_key(raw_key)
    return raw_key, key_hash, key_prefix

def hash_project_api_key(raw_key: str) -> str:
    """
    Computes a salted HMAC-SHA256 hash of the raw ingestion key.
    """
    return hmac.new(
        settings.INGESTION_KEY_SALT.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

def validate_api_key_format(raw_key: str) -> bool:
    """Checks if raw API key follows the expected 'pace_' prefix format and minimum length."""
    if not raw_key or not isinstance(raw_key, str):
        return False
    return raw_key.startswith("pace_") and len(raw_key) >= 16

def validate_environment_tag(env: str) -> bool:
    """Validates whether environment tag is an allowed deployment identifier."""
    if not env or not isinstance(env, str):
        return False
    allowed = {"production", "staging", "development", "test", "demo"}
    return env.strip().lower() in allowed

def format_token_count(count: int) -> str:
    """Formats token count into human readable metric standard (e.g. 1500 -> '1.5k')."""
    if count < 0:
        return "0"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}k"
    return str(count)

