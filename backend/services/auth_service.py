"""
backend/services/auth_service.py

Authentication and Identity Management Service for Milestone 7:
- Google Sign-In verification & account linking/provisioning
- Direct email/password registration & login with entropy enforcement
- JWT Session creation, token rotation, and multi-device revocation
- Anonymous guest session management
- Seamless Guest-to-User account merge engine
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from database.models import (
    User,
    UserRole,
    GuestSession,
    UserSession,
    AuthAuditLog,
    AssessmentAttempt,
)
from backend.core.security import (
    hash_password,
    verify_password,
    calculate_password_entropy,
    create_access_token,
    generate_opaque_token,
    hash_token,
    AuthRateLimiter,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from backend.services.selection.learner_model import LearnerModelService
from backend.services.admin_service import is_super_admin_email, SUPER_ADMIN_EMAILS
from backend.core.config import get_settings


class AuthService:
    """
    Core identity service handling authentication, session tokens, audit logging,
    and guest account merging.
    """

    # -------------------------------------------------------------------------
    # 1. Guest Session Management
    # -------------------------------------------------------------------------
    @staticmethod
    def create_guest_session(
        db: Session,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> GuestSession:
        """
        Creates an anonymous guest session token valid for 7 days.
        """
        token = generate_opaque_token(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        guest = GuestSession(
            id=str(uuid.uuid4()),
            session_token=token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        db.add(guest)
        db.commit()
        db.refresh(guest)
        return guest

    # -------------------------------------------------------------------------
    # 2. Google OAuth2 / OIDC Verification
    # -------------------------------------------------------------------------
    @staticmethod
    def authenticate_google(
        db: Session,
        id_token_str: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        mock_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Verifies a Google ID Token, links/creates a User, and issues tokens.
        Tests may inject already-verified claims with ``mock_payload`` when APP_ENV=test.
        """
        payload: Dict[str, Any] = {}
        
        settings = get_settings()

        if mock_payload:
            if not settings.allows_test_auth:
                raise ValueError("Mock Google authentication is available only in the test environment")
            payload = mock_payload
        else:
            if not settings.google_client_ids:
                raise ValueError("Google sign-in is not configured")
            try:
                from google.oauth2 import id_token
                from google.auth.transport import requests

                verification_error = None
                for client_id in settings.google_client_ids:
                    try:
                        payload = id_token.verify_oauth2_token(
                            id_token_str,
                            requests.Request(),
                            audience=client_id,
                            clock_skew_in_seconds=10,
                        )
                        break
                    except Exception as exc:
                        verification_error = exc
                else:
                    raise verification_error or ValueError("Token audience was not accepted")
            except Exception:
                raise ValueError("Invalid Google ID token")

        if payload.get("email_verified") is not True:
            raise ValueError("Google account email is not verified")
        if payload.get("iss") and payload.get("iss") not in {
            "accounts.google.com",
            "https://accounts.google.com",
        }:
            raise ValueError("Google ID token has an invalid issuer")

        email = payload.get("email", "").lower().strip()
        google_id = payload.get("sub") or payload.get("user_id")
        avatar_url = payload.get("picture")

        # Extract first name, last name, or full name
        given_name = payload.get("given_name", "").strip()
        family_name = payload.get("family_name", "").strip()
        if given_name and family_name:
            name = f"Dr. {given_name} {family_name}"
        elif given_name:
            name = f"Dr. {given_name}"
        elif payload.get("name"):
            raw_name = payload.get("name").strip()
            name = raw_name if raw_name.lower().startswith("dr.") else f"Dr. {raw_name}"
        else:
            name = f"Dr. {email.split('@')[0].replace('.', ' ').title()}"

        if not email or not google_id:
            raise ValueError("Google ID token missing email or subject identifier")

        # 1. Search existing user by google_id or email
        user = db.query(User).filter((User.google_id == google_id) | (User.email == email)).first()
        is_new_user = False

        is_super = is_super_admin_email(email)

        if not user:
            is_new_user = True
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                name=name,
                google_id=google_id,
                avatar_url=avatar_url,
                is_email_verified=True,
                role=UserRole.SUPER_ADMIN if is_super else UserRole.USER,
                target_exam="NEET_SS",
                primary_speciality="Oncopathology",
            )
            db.add(user)
            db.flush()
        else:
            # Update user info with latest Google profile data
            if is_super and user.role != UserRole.SUPER_ADMIN:
                user.role = UserRole.SUPER_ADMIN
            if not user.google_id:
                user.google_id = google_id
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            if name and (not user.name or user.name == "Medical Resident"):
                user.name = name
            if not user.is_email_verified or is_super:
                user.is_email_verified = True
            db.flush()

        # 2. Issue session & tokens
        session_data = AuthService._create_user_session(db, user, ip_address, user_agent)
        
        # 3. Audit log
        AuthService._log_auth_event(
            db, user.id, email, "GOOGLE_OAUTH_LOGIN", ip_address, user_agent
        )
        db.commit()

        return {
            "access_token": session_data["access_token"],
            "refresh_token": session_data["refresh_token"],
            "token_type": "bearer",
            "is_new_user": is_new_user,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "avatar_url": user.avatar_url,
                "target_exam": user.target_exam,
                "residency_stage": user.residency_stage,
                "has_password": bool(user.password_hash),
            },
        }

    # -------------------------------------------------------------------------
    # 3. Direct Email & Password Registration & Login
    # -------------------------------------------------------------------------
    @staticmethod
    def register_email_password(
        db: Session,
        email: str,
        password: str,
        name: str,
        target_exam: Optional[str] = "NEET_SS",
        residency_stage: Optional[str] = None,
        medical_college: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registers a new user with email and password after validating password entropy.
        """
        email = email.lower().strip()
        if not email or "@" not in email:
            raise ValueError("Invalid email format")

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise ValueError("An account with this email already exists")

        # Evaluate password strength
        strength_eval = calculate_password_entropy(password)
        if not strength_eval["is_acceptable"]:
            feedback_str = ", ".join(strength_eval["feedback"])
            raise ValueError(f"Password is too weak: {feedback_str}")

        is_super = is_super_admin_email(email)
        hashed_pwd = hash_password(password)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name.strip(),
            password_hash=hashed_pwd,
            role=UserRole.SUPER_ADMIN if is_super else UserRole.USER,
            target_exam=target_exam or "NEET_SS",
            residency_stage=residency_stage,
            medical_college=medical_college,
            primary_speciality="Pathology",
            is_email_verified=True if is_super else False,
        )
        db.add(user)
        db.flush()

        session_data = AuthService._create_user_session(db, user, ip_address, user_agent)
        AuthService._log_auth_event(db, user.id, email, "PASSWORD_REGISTER", ip_address, user_agent)
        db.commit()

        return {
            "access_token": session_data["access_token"],
            "refresh_token": session_data["refresh_token"],
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "target_exam": user.target_exam,
                "residency_stage": user.residency_stage,
                "has_password": True,
            },
        }

    @staticmethod
    def login_email_password(
        db: Session,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Logs in an existing user with rate-limiting protection.
        """
        email = email.lower().strip()
        rate_key = f"{email}:{ip_address or '0.0.0.0'}"

        # 1. Check rate limit
        is_locked, remaining_sec = AuthRateLimiter.is_locked_out(rate_key)
        if is_locked:
            raise ValueError(f"Too many failed login attempts. Please try again in {remaining_sec} seconds.")

        # 2. Query user
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            AuthRateLimiter.record_failure(rate_key)
            AuthService._log_auth_event(db, user.id if user else None, email, "LOGIN_FAILED", ip_address, user_agent)
            db.commit()
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("This account has been deactivated. Please contact support.")

        # Auto-elevate super admin if email matches
        if is_super_admin_email(user.email) and user.role != UserRole.SUPER_ADMIN:
            user.role = UserRole.SUPER_ADMIN
            user.is_email_verified = True
            db.flush()

        # Reset rate limiter upon success
        AuthRateLimiter.reset(rate_key)

        session_data = AuthService._create_user_session(db, user, ip_address, user_agent)
        AuthService._log_auth_event(db, user.id, email, "LOGIN_SUCCESS", ip_address, user_agent)
        db.commit()

        return {
            "access_token": session_data["access_token"],
            "refresh_token": session_data["refresh_token"],
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "avatar_url": user.avatar_url,
                "target_exam": user.target_exam,
                "residency_stage": user.residency_stage,
                "has_password": True,
            },
        }

    # -------------------------------------------------------------------------
    # 4. Password Provisioning & Updates
    # -------------------------------------------------------------------------
    @staticmethod
    def set_or_update_password(db: Session, user_id: str, new_password: str) -> Dict[str, Any]:
        """
        Sets or changes the password for an existing authenticated user.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        strength = calculate_password_entropy(new_password)
        if not strength["is_acceptable"]:
            feedback_str = ", ".join(strength["feedback"])
            raise ValueError(f"Password is too weak: {feedback_str}")

        user.password_hash = hash_password(new_password)
        AuthService._log_auth_event(db, user.id, user.email, "PASSWORD_SET_OR_UPDATED")
        db.commit()
        return {"success": True, "message": "Password updated successfully"}

    # -------------------------------------------------------------------------
    # 5. Token Rotation & Multi-Device Logout
    # -------------------------------------------------------------------------
    @staticmethod
    def refresh_session(
        db: Session,
        refresh_token_str: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Rotates an existing refresh token and issues a fresh 15-minute access token.
        """
        token_hash = hash_token(refresh_token_str)
        session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()

        now = datetime.now(timezone.utc)
        if not session or session.is_revoked:
            raise ValueError("Invalid or expired refresh token")
        
        expires = session.expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires and expires < now:
            raise ValueError("Invalid or expired refresh token")

        user = db.query(User).filter(User.id == session.user_id).first()
        if not user or not user.is_active:
            raise ValueError("User account is inactive or not found")

        # Generate new rotated refresh token
        new_refresh_token = generate_opaque_token(32)
        session.refresh_token_hash = hash_token(new_refresh_token)
        session.last_used_at = now
        if ip_address:
            session.ip_address = ip_address
        if user_agent:
            session.user_agent = user_agent

        new_access_token = create_access_token({
            "sub": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        })

        db.commit()
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def logout(db: Session, refresh_token_str: str) -> bool:
        """Revokes a specific refresh token session."""
        token_hash = hash_token(refresh_token_str)
        session = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).first()
        if session:
            session.is_revoked = True
            db.commit()
            return True
        return False

    @staticmethod
    def logout_all(db: Session, user_id: str) -> int:
        """Revokes all active sessions for a user across all devices."""
        updated = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,
        ).update({"is_revoked": True})
        db.commit()
        return updated

    # -------------------------------------------------------------------------
    # 6. Guest Session Account Merge Engine
    # -------------------------------------------------------------------------
    @staticmethod
    def merge_guest_session(
        db: Session,
        guest_session_token: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Transfers all diagnostic assessment attempts and questions from an anonymous
        guest session into the newly authenticated user account, populating learner history and mastery.
        """
        guest = db.query(GuestSession).filter(GuestSession.session_token == guest_session_token).first()
        if not guest:
            return {"merged": False, "reason": "Guest session not found"}

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found for guest merge")

        # Find all attempts tied to this guest session
        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.guest_session_id == guest.id
        ).all()

        merged_count = 0
        now = datetime.now(timezone.utc)

        for att in attempts:
            att.user_id = user.id
            merged_count += 1
            
            # If attempt was submitted, backfill learner history & mastery
            if att.submitted_at and att.attempt_questions:
                LearnerModelService.record_attempt_history(db, att)

        guest.converted_user_id = user.id
        guest.merged_at = now
        db.commit()

        return {
            "merged": True,
            "guest_session_id": guest.id,
            "merged_attempts_count": merged_count,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _create_user_session(
        db: Session,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, str]:
        refresh_token = generate_opaque_token(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        session = UserSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        db.add(session)

        access_token = create_access_token({
            "sub": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @staticmethod
    def _log_auth_event(
        db: Session,
        user_id: Optional[str],
        email: str,
        event_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        log = AuthAuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            email=email,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
