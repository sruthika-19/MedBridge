import os
from dotenv import load_dotenv

from typing import Callable
load_dotenv(".env.local")

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not set.")

if not SUPABASE_PUBLISHABLE_KEY:
    raise RuntimeError("SUPABASE_PUBLISHABLE_KEY is not set.")

if not SUPABASE_SECRET_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY is not set.")


# Client for verifying Supabase Auth JWTs
auth_client: Client = create_client(
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY,
)


# Backend-only client for reading application roles.
# The secret key must NEVER reach the browser.
db_client: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Verify the incoming Supabase access token."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "errorCode": "AUTH_REQUIRED",
                "message": "Authentication required.",
                "data": [],
            },
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "errorCode": "AUTH_REQUIRED",
                "message": "Bearer authentication required.",
                "data": [],
            },
        )

    token = credentials.credentials

    try:
        response = auth_client.auth.get_claims(token)

        claims = response.get("claims") if response else None

        if not claims:
            raise ValueError("No verified JWT claims returned.")

        user_id = claims.get("sub")

        if not user_id:
            raise ValueError("JWT does not contain a user ID.")

        return {
            "user_id": user_id,
            "email": claims.get("email"),
            "claims": claims,
        }

    except Exception as exc:
        print(f"JWT verification failed: {exc}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "errorCode": "AUTH_REQUIRED",
                "message": "Invalid or expired access token.",
                "data": [],
            },
        )


def get_user_role(user_id: str) -> str | None:
    """Read the MedBridge application role from user_roles."""

    try:
        response = (
            db_client
            .table("user_roles")
            .select("role")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            return None

        return rows[0].get("role")

    except Exception as exc:
        print(f"Role lookup failed: {exc}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "errorCode": "DATABASE_ERROR",
                "message": "Unable to determine application role.",
                "data": [],
            },
        )


def require_authenticated_user(
    current_user: dict = Depends(get_current_user),
):
    """Allow any authenticated MedBridge user with an assigned role."""

    role = get_user_role(current_user["user_id"])

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "errorCode": "ACCESS_DENIED",
                "message": "No MedBridge role is assigned to this account.",
                "data": [],
            },
        )

    current_user["role"] = role

    return current_user


def require_role(required_role: str) -> Callable:
    """Require a specific MedBridge application role."""

    def role_dependency(
        current_user: dict = Depends(get_current_user),
    ):
        role = get_user_role(current_user["user_id"])

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "errorCode": "ACCESS_DENIED",
                    "message": "No MedBridge role is assigned to this account.",
                    "data": [],
                },
            )

        if role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "errorCode": "ACCESS_DENIED",
                    "message": f"{required_role.capitalize()} access required.",
                    "data": [],
                },
            )

        current_user["role"] = role

        return current_user

    return role_dependency
