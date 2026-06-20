"""Authentication and user context routes."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..middleware import get_user_context, require_ownership, format_error_response
from ..config import get_settings
from supabase import create_client

router = APIRouter(prefix="/api/auth", tags=["authentication"])
settings = get_settings()
supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
supabase = create_client(settings.SUPABASE_URL, supabase_key)


class UserContextResponse(BaseModel):
    """User context response model."""
    user_id: str
    email: str
    full_name: Optional[str] = ""
    facility_id: Optional[str] = None
    facility_name: Optional[str] = ""
    industry: Optional[str] = ""
    role: Optional[str] = None
    critical_asset: Optional[str] = ""
    technician_count: Optional[int] = 0
    modules_selected: Optional[List[str]] = []
    priorities: Optional[List[str]] = []
    setup_complete: Optional[bool] = False
    account_type: Optional[str] = "sandbox"
    query_count: Optional[int] = 0
    session_expires_at: Optional[str] = None


@router.get("/user/context", response_model=UserContextResponse)
async def get_user_context_endpoint(context: dict = Depends(get_user_context)):
    """
    Get complete user context including facility, role, and permissions.
    This is called on every dashboard page load to render the correct experience.
    """
    user_id = context["user_id"]
    email = context["email"] or ""
    facility = context.get("facility") or {}
    role = context.get("role")
    profile = context.get("profile") or {}
    
    # Extract fields from nested structures
    full_name = profile.get("full_name", "") or profile.get("company_name", "")
    if not full_name and email:
        full_name = email.split("@")[0]
        
    facility_id = facility.get("id") or profile.get("current_facility_id")
    facility_name = facility.get("name", "")
    industry = facility.get("industry", "")
    critical_asset = facility.get("critical_asset", "")
    technician_count = facility.get("technician_count", 0)
    modules_selected = facility.get("modules_selected", [])
    priorities = facility.get("priorities", [])
    setup_complete = facility.get("setup_complete", False)
    account_type = facility.get("account_type", "sandbox")
    query_count = facility.get("query_count", 0)
    session_expires_at = facility.get("session_expires_at")
    
    return UserContextResponse(
        user_id=user_id,
        email=email,
        full_name=full_name,
        facility_id=facility_id,
        facility_name=facility_name,
        industry=industry,
        role=role,
        critical_asset=critical_asset,
        technician_count=technician_count,
        modules_selected=modules_selected,
        priorities=priorities,
        setup_complete=setup_complete,
        account_type=account_type,
        query_count=query_count,
        session_expires_at=session_expires_at
    )



def calculate_permissions(role: Optional[str]) -> Dict[str, bool]:
    """Calculate user permissions based on role."""
    if not role:
        return {
            "can_manage_team": False,
            "can_delete": False,
            "can_view_compliance": False,
            "can_create": False
        }
    
    # Role hierarchy: owner > supervisor > technician > viewer
    return {
        "can_manage_team": role == "owner",
        "can_delete": role in ["owner", "supervisor"],
        "can_view_compliance": role in ["owner", "supervisor"],
        "can_create": role in ["owner", "supervisor", "technician"]
    }


class FacilitySetupCheck(BaseModel):
    """Check if user needs to go through setup."""
    needs_setup: bool
    has_facility: bool


@router.get("/user/setup-check", response_model=FacilitySetupCheck)
async def check_setup_status(context: dict = Depends(get_user_context)):
    """
    Check if user needs to go through setup wizard.
    Returns true if user has no facility or facility setup is not complete.
    """
    facility = context.get("facility")
    
    if not facility:
        return FacilitySetupCheck(needs_setup=True, has_facility=False)
    
    needs_setup = not facility.get("setup_complete", False)
    
    return FacilitySetupCheck(
        needs_setup=needs_setup,
        has_facility=True
    )


@router.post("/user/switch-facility")
async def switch_facility(
    facility_id: str,
    context: dict = Depends(get_user_context)
):
    """
    Switch user's current facility.
    User must be a member of the target facility.
    """
    user_id = context["user_id"]
    
    try:
        # Check if user is a member of the target facility
        member_response = supabase.table("facility_members").select("*").eq(
            "facility_id", facility_id
        ).eq("user_id", user_id).eq("status", "active").single()
        
        if not member_response.data:
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this facility"
            )
        
        # Update user's current facility
        supabase.table("profiles").update({
            "current_facility_id": facility_id,
            "updated_at": datetime.now().isoformat()
        }).eq("id", user_id).execute()
        
        return {"success": True, "message": "Facility switched successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("SWITCH_FAILED", "Failed to switch facility", str(e))
        )


@router.post("/logout")
async def logout():
    """
    Logout endpoint.
    Client-side should clear the JWT token.
    """
    return {"success": True, "message": "Logged out successfully"}


class ProfileCreateRequest(BaseModel):
    """Request model for creating a profile."""
    user_id: str
    full_name: str
    company_name: str
    email: str


@router.post("/create-profile")
async def create_profile(profile_data: ProfileCreateRequest):
    """
    Create a profile record for a new user.
    This is called after successful account creation.
    """
    try:
        profile_record = {
            "id": profile_data.user_id,
            "full_name": profile_data.full_name,
            "company_name": profile_data.company_name,
            "email": profile_data.email,
            "current_facility_id": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("profiles").insert(profile_record).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create profile"
            )
        
        return {"success": True, "message": "Profile created successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("PROFILE_CREATE_FAILED", "Failed to create profile", str(e))
        )
