"""Authentication and role-based authorization middleware."""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from supabase import create_client, Client
from .config import get_settings

settings = get_settings()

# Initialize Supabase client (service role if available, else anon)
supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
supabase: Client = create_client(settings.SUPABASE_URL, supabase_key)

security = HTTPBearer(auto_error=False)

# Role hierarchy for permission checking
ROLE_HIERARCHY = {
    "owner": 4,
    "supervisor": 3,
    "technician": 2,
    "viewer": 1,
}


async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Verify Supabase JWT token and return user info.

    Attempts Supabase verification first; if that fails, falls back to
    decoding a locally-signed JWT issued by the backend (demo mode).
    """
    # If no credentials provided, return a guest demo user
    if not credentials:
        import uuid
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        return {"user_id": guest_id, "email": f"{guest_id}@local", "token": f"guest_token_{guest_id}"}
    # If no credentials provided, return guest demo user
    if not credentials:
        import uuid
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        return {"user_id": guest_id, "email": f"{guest_id}@local", "token": f"guest_token_{guest_id}", "is_guest": True}

    token = credentials.credentials

    # Try Supabase verification
    try:
        user_response = supabase.auth.get_user(token)
        if user_response and getattr(user_response, "user", None):
            return {"user_id": user_response.user.id, "email": user_response.user.email, "token": token}
    except Exception:
        # Supabase may reject demo tokens — fall back to local JWT
        pass

    # Fall back to locally-signed JWT; if decoding fails, return guest demo user
    try:
        from jose import jwt

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise Exception("Invalid local JWT")
        return {"user_id": user_id, "email": f"{user_id}@local", "token": token}
    except Exception:
        import uuid
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        return {"user_id": guest_id, "email": f"{guest_id}@local", "token": f"guest_token_{guest_id}", "is_guest": True}


async def get_user_context(auth_data: dict = Depends(verify_token)) -> dict:
    """Get complete user context including facility and role.

    If Supabase profile/facility data is missing, returns a partial context
    that allows demo users to operate in a limited mode.
    """
    user_id = auth_data["user_id"]

    try:
        # If user_id is not a UUID (e.g. demo/local token like 'admin'),
        # skip Supabase lookups and return a partial context.
        import uuid as _uuid
        try:
            _uuid.UUID(str(user_id))
        except Exception:
            return {"user_id": user_id, "email": auth_data.get("email"), "facility_id": None, "role": None, "facility": None, "profile": None}

        # Get user profile
        profile_response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        if not getattr(profile_response, "data", None):
            return {"user_id": user_id, "email": auth_data.get("email"), "facility_id": None, "role": None, "facility": None, "profile": None}

        profile = profile_response.data
        facility_id = profile.get("current_facility_id")

        if not facility_id:
            return {"user_id": user_id, "email": auth_data.get("email"), "facility_id": None, "role": None, "facility": None, "profile": profile}

        # Get facility
        facility_response = supabase.table("facilities").select("*").eq("id", facility_id).single().execute()
        if not getattr(facility_response, "data", None):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
        facility = facility_response.data

        # Get user's role in this facility
        member_response = supabase.table("facility_members").select("*").eq("facility_id", facility_id).eq("user_id", user_id).eq("status", "active").single().execute()
        if not getattr(member_response, "data", None):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not a member of this facility")

        role = member_response.data.get("role")

        return {"user_id": user_id, "email": auth_data.get("email"), "facility_id": facility_id, "role": role, "facility": facility, "profile": profile}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get user context: {str(e)}")


def role_check(required_role: str):
    """Dependency factory that checks if user has at least the required role level."""

    async def check_role(context: dict = Depends(get_user_context)) -> dict:
        user_role = context.get("role")
        if not user_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No role assigned")

        user_role_level = ROLE_HIERARCHY.get(user_role, 0)
        required_role_level = ROLE_HIERARCHY.get(required_role, 0)
        if user_role_level < required_role_level:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Insufficient permissions. Required role: {required_role}, Current role: {user_role}")
        return context

    return check_role


def require_ownership(context: dict = Depends(get_user_context)) -> dict:
    return role_check("owner")(context)


def require_supervisor(context: dict = Depends(get_user_context)) -> dict:
    return role_check("supervisor")(context)


def require_technician(context: dict = Depends(get_user_context)) -> dict:
    return role_check("technician")(context)


def require_viewer(context: dict = Depends(get_user_context)) -> dict:
    return role_check("viewer")(context)


def facility_access_check(context: dict = Depends(get_user_context)) -> dict:
    return context


async def check_rate_limit(user_id: str, action: str, limit: int = 10) -> bool:
    return True


async def check_sandbox_limits(context: dict, action: str) -> bool:
    facility = context.get("facility")
    if not facility or facility.get("account_type") != "sandbox":
        return True
    if action == "query" and facility.get("query_count", 0) >= 2:
        return False
    return True


def format_error_response(error_code: str, message: str, detail: Optional[str] = None) -> dict:
    response = {"error": message, "code": error_code}
    if detail:
        response["detail"] = detail
    return response
