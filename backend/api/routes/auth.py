"""
backend/api/routes/auth.py

FastAPI router for Authentication, Session Management, and Guest Merging (Milestone 7).
"""

from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_engine, get_session_factory
from database.models import User
from backend.core.security import decode_access_token, generate_crypto_password, calculate_password_entropy
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication & Identity"])


def get_db():
    engine = get_engine()
    session_factory = get_session_factory(engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated or not found",
        )
    return user


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class GoogleAuthRequest(BaseModel):
    id_token: Optional[str] = Field(None, description="Google ID token string or simulated token")
    email: Optional[str] = Field(None, description="Direct Google account email")
    token: Optional[str] = Field(None, description="Alternative token field")


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    target_exam: Optional[str] = "NEET_SS"
    residency_stage: Optional[str] = None
    medical_college: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class SetPasswordRequest(BaseModel):
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class MergeGuestRequest(BaseModel):
    guest_session_token: str


class EvaluatePasswordRequest(BaseModel):
    password: str


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.post("/guest-session")
def create_guest_session(request: Request, db: Session = Depends(get_db)):
    """Creates an anonymous guest session token valid for 7 days."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    guest = AuthService.create_guest_session(db, ip_address=ip, user_agent=ua)
    return {
        "guest_session_token": guest.session_token,
        "expires_at": guest.expires_at.isoformat(),
    }


@router.post("/google")
def google_sign_in(
    req: GoogleAuthRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticates or provisions a user using a Google ID token, simulated token, or email."""
    token_or_email = req.id_token or req.email or req.token
    if not token_or_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google ID token or email in request body",
        )
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        res = AuthService.authenticate_google(db, token_or_email, ip_address=ip, user_agent=ua)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/register")
def register_with_password(
    req: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Registers a new user with email and password."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        res = AuthService.register_email_password(
            db=db,
            email=req.email,
            password=req.password,
            name=req.name,
            target_exam=req.target_exam,
            residency_stage=req.residency_stage,
            medical_college=req.medical_college,
            ip_address=ip,
            user_agent=ua,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
def login_with_password(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticates an existing user with email and password."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        res = AuthService.login_email_password(
            db=db,
            email=req.email,
            password=req.password,
            ip_address=ip,
            user_agent=ua,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh")
def refresh_token(
    req: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Rotates refresh token and issues fresh access token."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        res = AuthService.refresh_session(db, req.refresh_token, ip_address=ip, user_agent=ua)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
def logout(
    req: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revokes the active refresh token session."""
    AuthService.logout(db, req.refresh_token)
    return {"success": True, "message": "Logged out successfully"}


@router.post("/logout-all")
def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revokes all active sessions for the user across all devices."""
    count = AuthService.logout_all(db, current_user.id)
    return {"success": True, "revoked_sessions_count": count}


@router.post("/set-password")
def set_password(
    req: SetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sets or updates the password for the current authenticated user."""
    try:
        res = AuthService.set_or_update_password(db, current_user.id, req.password)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/generate-password")
def generate_password(length: int = 20):
    """Generates a cryptographically strong suggested password string."""
    pwd = generate_crypto_password(length)
    entropy_info = calculate_password_entropy(pwd)
    return {"password": pwd, "entropy": entropy_info}


@router.post("/evaluate-password")
def evaluate_password(req: EvaluatePasswordRequest):
    """Evaluates password entropy bits, strength tier, and feedback."""
    return calculate_password_entropy(req.password)


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user profile and roles."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        "avatar_url": current_user.avatar_url,
        "target_exam": current_user.target_exam,
        "target_year": current_user.target_year,
        "medical_college": current_user.medical_college,
        "residency_stage": current_user.residency_stage,
        "primary_speciality": current_user.primary_speciality,
        "current_streak": current_user.current_streak,
        "longest_streak": current_user.longest_streak,
        "has_password": bool(current_user.password_hash),
        "is_subscribed": current_user.is_subscribed,
    }


@router.post("/merge-guest")
def merge_guest_session(
    req: MergeGuestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Merges anonymous guest diagnostic attempts and mastery into user account."""
    res = AuthService.merge_guest_session(db, req.guest_session_token, current_user.id)
    return res
