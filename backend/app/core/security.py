"""
Security utilities: JWT token management, password hashing, and API key encryption.
"""
import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ─── Password Hashing ────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Tokens ──────────────────────────────────────────────────────────────

def create_access_token(
    subject: Any,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """Create a signed JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload: dict = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Any) -> str:
    """Create a signed JWT refresh token with a longer expiry."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.
    Raises JWTError if invalid or expired.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify token signature, expiry, and type.
    Returns the subject (user ID) on success, None on failure.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != token_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None


# ─── API Key Encryption ───────────────────────────────────────────────────────

def _get_fernet() -> Fernet:
    """
    Get or generate a Fernet symmetric encryption instance.
    In production, ENCRYPTION_KEY must be set in the environment.
    """
    key = settings.ENCRYPTION_KEY
    if not key:
        # Auto-generate in dev; log a warning
        import structlog
        log = structlog.get_logger()
        log.warning(
            "ENCRYPTION_KEY not set — generating ephemeral key. "
            "Encrypted API keys will NOT survive a restart. "
            "Set ENCRYPTION_KEY in production!"
        )
        key = Fernet.generate_key().decode()
    else:
        # Accept raw base64 or already-encoded Fernet key
        try:
            key_bytes = key.encode() if isinstance(key, str) else key
            base64.urlsafe_b64decode(key_bytes + b"==")  # validate format
        except Exception:
            key = base64.urlsafe_b64encode(key.encode()[:32].ljust(32, b"0")).decode()

    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an exchange API key/secret before storing in the database."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt an exchange API key/secret retrieved from the database."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


# ─── Utilities ────────────────────────────────────────────────────────────────

def generate_api_key_pair() -> tuple[str, str]:
    """Generate a random internal API key + secret for the strategy marketplace."""
    api_key = base64.urlsafe_b64encode(os.urandom(24)).decode()
    api_secret = base64.urlsafe_b64encode(os.urandom(48)).decode()
    return api_key, api_secret
