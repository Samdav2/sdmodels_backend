from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import base64
import binascii
from pathlib import Path
import jwt  # PyJWT library
import bcrypt
from fastapi import HTTPException, status

from app.core.config import settings


def _decode_key_env(value: str) -> bytes:
    """
    Parse a key from an environment variable.

    Handles three formats:
    1. Raw PEM (starts with '-----BEGIN ...') — returned as-is.
    2. PEM with literal \\n escapes (Render stores multiline vars this way).
    3. Base64-encoded PEM — decoded first.
    """
    value = value.strip()

    # Replace literal \n escape sequences (common in CI/CD env vars)
    if "\\n" in value:
        value = value.replace("\\n", "\n")

    # If it looks like a PEM block, use it directly
    if value.startswith("-----BEGIN"):
        return value.encode("utf-8")

    # Otherwise treat as base64
    padding = 4 - (len(value) % 4)
    if padding != 4:
        value += "=" * padding
    try:
        return base64.b64decode(value)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Invalid base64 key: {exc}") from exc


def _load_rsa_key(key_type: str) -> bytes:
    """Load RSA key from file or environment variable and return as bytes"""
    if key_type == "private":
        if settings.JWT_PRIVATE_KEY:
            return _decode_key_env(settings.JWT_PRIVATE_KEY)
        key_path = Path(settings.JWT_PRIVATE_KEY_PATH)
        if key_path.exists():
            return key_path.read_bytes()
        raise ValueError("JWT private key not found. Run: python scripts/generate_rsa_keys.py")
    else:  # public
        if settings.JWT_PUBLIC_KEY:
            return _decode_key_env(settings.JWT_PUBLIC_KEY)
        key_path = Path(settings.JWT_PUBLIC_KEY_PATH)
        if key_path.exists():
            return key_path.read_bytes()
        raise ValueError("JWT public key not found. Run: python scripts/generate_rsa_keys.py")



# Load RSA keys at module initialization
try:
    PRIVATE_KEY = _load_rsa_key("private")
    PUBLIC_KEY = _load_rsa_key("public")
    print("✅ RSA keys loaded successfully")
except ValueError as e:
    print(f"⚠️  Warning: {e}")
    print("   Tokens will not work until RSA keys are generated.")
    PRIVATE_KEY = None
    PUBLIC_KEY = None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token using RSA private key"""
    if not PRIVATE_KEY:
        raise ValueError("JWT private key not loaded. Cannot create tokens.")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token using RSA private key"""
    if not PRIVATE_KEY:
        raise ValueError("JWT private key not loaded. Cannot create tokens.")

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify JWT token using RSA public key"""
    if not PUBLIC_KEY:
        raise ValueError("JWT public key not loaded. Cannot verify tokens.")

    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt has a 72-byte limit; truncate to avoid ValueError
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    # Truncate to bcrypt's 72-byte limit before hashing
    password_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")
