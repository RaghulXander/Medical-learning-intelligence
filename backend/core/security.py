"""
backend/core/security.py

Enterprise security utilities for Milestone 7:
- Cryptographic password hashing & verification
- Live password entropy calculator (bits of entropy + tier)
- High-entropy cryptographic strong password generator
- JWT Access (15m) and Refresh (30d) token generation and verification
- Refresh token SHA-256 hashing for secure database storage
- Rate limiter for authentication brute-force prevention
"""

import re
import math
import secrets
import string
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple, List

from backend.core.config import get_settings

# Configuration constants
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


# -----------------------------------------------------------------------------
# 1. Password Hashing & Verification
# -----------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """
    Generates a secure salted cryptographic hash (PBKDF2-HMAC-SHA256, 100,000 iterations).
    Format: pbkdf2_sha256$iterations$salt$hash
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    salt = secrets.token_hex(16)
    iterations = 100_000
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored salted hash using constant-time comparison.
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        
        iterations = int(parts[1])
        salt = parts[2]
        expected_key_hex = parts[3]
        
        computed_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(computed_key.hex(), expected_key_hex)
    except Exception:
        return False


# -----------------------------------------------------------------------------
# 2. Password Entropy & Strength Evaluator
# -----------------------------------------------------------------------------
def calculate_password_entropy(password: str) -> Dict[str, Any]:
    """
    Calculates the Shannon entropy (bits) of a password based on length and character space.
    Returns score (0-100), entropy bits, strength label, and actionable feedback suggestions.
    """
    if not password:
        return {
            "entropy_bits": 0.0,
            "score": 0,
            "strength": "WEAK",
            "feedback": ["Password is required"],
            "is_acceptable": False,
        }

    pool_size = 0
    has_lower = bool(re.search(r"[a-z]", password))
    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_symbol = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password))

    if has_lower:
        pool_size += 26
    if has_upper:
        pool_size += 26
    if has_digit:
        pool_size += 10
    if has_symbol:
        pool_size += 32

    if pool_size == 0:
        pool_size = 26

    # E = L * log2(R)
    entropy_bits = round(len(password) * math.log2(pool_size), 1)

    feedback: List[str] = []
    if len(password) < 8:
        feedback.append("Use at least 8 characters")
    if not has_upper:
        feedback.append("Add uppercase letters")
    if not has_lower:
        feedback.append("Add lowercase letters")
    if not has_digit:
        feedback.append("Add numbers")
    if not has_symbol:
        feedback.append("Add special symbols (!@#$%)")

    # Score calculation (capped at 100)
    score = min(100, int((entropy_bits / 80.0) * 100))

    if entropy_bits < 40:
        strength = "WEAK"
    elif entropy_bits < 60:
        strength = "MODERATE"
    elif entropy_bits < 80:
        strength = "STRONG"
    else:
        strength = "VERY_STRONG"

    return {
        "entropy_bits": entropy_bits,
        "score": score,
        "strength": strength,
        "feedback": feedback,
        "is_acceptable": len(password) >= 8 and entropy_bits >= 40,
    }


# -----------------------------------------------------------------------------
# 3. Cryptographic Strong Password Generator
# -----------------------------------------------------------------------------
def generate_crypto_password(length: int = 20) -> str:
    """
    Generates a cryptographically strong, high-entropy password guaranteed to contain
    uppercase, lowercase, digits, and punctuation symbols.
    """
    length = max(16, min(64, length))
    
    # Ensure at least 3 chars from each category
    lowers = [secrets.choice(string.ascii_lowercase) for _ in range(3)]
    uppers = [secrets.choice(string.ascii_uppercase) for _ in range(3)]
    digits = [secrets.choice(string.digits) for _ in range(3)]
    symbols = [secrets.choice("!@#$%^&*_-+=") for _ in range(3)]
    
    # Fill remaining length from combined pool
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*_-+="
    remaining = [secrets.choice(all_chars) for _ in range(length - 12)]
    
    pwd_list = lowers + uppers + digits + symbols + remaining
    secrets.SystemRandom().shuffle(pwd_list)
    return "".join(pwd_list)


# -----------------------------------------------------------------------------
# 4. Token Utilities (JWT & SHA-256 Hashing)
# -----------------------------------------------------------------------------
def hash_token(token: str) -> str:
    """Computes a SHA-256 hex digest of an opaque token for database lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_opaque_token(nbytes: int = 32) -> str:
    """Generates a cryptographically secure random token string."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a signed JWT access token.
    Uses standard lightweight HMAC-SHA256 JWT encoding.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"iat": int(now.timestamp()), "exp": int(expire.timestamp())})
    
    # Simple, zero-dependency JWT HS256 encoder
    import json
    import base64
    
    def b64url(val: bytes) -> str:
        return base64.urlsafe_b64encode(val).decode("utf-8").rstrip("=")
    
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    hdr_b64 = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))
    
    signing_input = f"{hdr_b64}.{payload_b64}".encode("utf-8")
    secret = get_settings().jwt_secret_key
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = b64url(sig)
    
    return f"{hdr_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and validates a JWT access token signature and expiration.
    Returns payload dict if valid, or None if expired/tampered.
    """
    try:
        import json
        import base64
        
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        hdr_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        signing_input = f"{hdr_b64}.{payload_b64}".encode("utf-8")
        secret = get_settings().jwt_secret_key
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        
        # Base64 pad
        pad = "=" * ((4 - len(sig_b64) % 4) % 4)
        actual_sig = base64.urlsafe_b64decode(sig_b64 + pad)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        # Decode payload
        pad_p = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + pad_p)
        payload = json.loads(payload_bytes.decode("utf-8"))
        
        # Check exp
        exp = payload.get("exp")
        if exp and exp < datetime.now(timezone.utc).timestamp():
            return None
        
        return payload
    except Exception:
        return None


# -----------------------------------------------------------------------------
# 5. In-Memory Brute-Force Rate Limiter
# -----------------------------------------------------------------------------
class AuthRateLimiter:
    """Tracks failed login attempts per key (IP or email) to prevent brute force."""
    _attempts: Dict[str, List[datetime]] = {}

    @classmethod
    def record_failure(cls, key: str) -> None:
        now = datetime.now(timezone.utc)
        if key not in cls._attempts:
            cls._attempts[key] = []
        cls._attempts[key].append(now)

    @classmethod
    def is_locked_out(cls, key: str) -> Tuple[bool, int]:
        """
        Returns (is_locked, remaining_lockout_seconds).
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        
        # Purge expired attempts
        if key in cls._attempts:
            cls._attempts[key] = [t for t in cls._attempts[key] if t > cutoff]
            if len(cls._attempts[key]) >= MAX_LOGIN_ATTEMPTS:
                oldest_in_window = min(cls._attempts[key])
                remaining = int((oldest_in_window + timedelta(minutes=LOCKOUT_DURATION_MINUTES) - now).total_seconds())
                return True, max(1, remaining)
        
        return False, 0

    @classmethod
    def reset(cls, key: str) -> None:
        cls._attempts.pop(key, None)
