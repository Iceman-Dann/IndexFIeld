"""Facility management routes."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import os

from ..middleware import get_user_context, require_ownership, format_error_response
from ..config import get_settings
from supabase import create_client

router = APIRouter(prefix="/api/facility", tags=["facility"])
settings = get_settings()
supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
supabase = create_client(settings.SUPABASE_URL, supabase_key)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY") or getattr(settings, "RESEND_API_KEY", None)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8000")


async def send_invite_email(to_email: str, facility_name: str, role: str,
                             inviter_name: str, token: str,
                             personal_message: Optional[str] = None):
    """Send invite email via Resend. Silently skips if no API key configured."""
    if not RESEND_API_KEY:
        return
    try:
        import httpx
        accept_url = f"{FRONTEND_URL}/setup-wizard.html?invite={token}"
        body_lines = []
        if personal_message:
            body_lines.append(f"<p style='color:#94A3B8'>{personal_message}</p>")
        body_html = f"""
        <div style='font-family:Inter,sans-serif;background:#111827;color:#F8FAFC;padding:32px;border-radius:12px;max-width:520px'>
          <img src='{FRONTEND_URL}/favicon.png' width='40' style='border-radius:8px;margin-bottom:16px'>
          <h2 style='color:#F97316;margin:0 0 8px'>You've been invited to {facility_name}</h2>
          <p style='color:#94A3B8'>You've been invited by <strong style='color:#F8FAFC'>{inviter_name}</strong> to join <strong style='color:#F8FAFC'>{facility_name}</strong> on IndexField as a <strong style='color:#F97316'>{role}</strong>.</p>
          {''.join(body_lines)}
          <a href='{accept_url}' style='display:inline-block;margin-top:24px;padding:12px 28px;background:#F97316;color:#111827;font-weight:700;border-radius:8px;text-decoration:none'>Accept Invitation</a>
          <p style='color:#475569;font-size:11px;margin-top:24px'>This invite expires in 7 days. If you did not expect this, you can safely ignore it.</p>
        </div>
        """
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={
                    "from": "IndexField <noreply@indexfield.app>",
                    "to": [to_email],
                    "subject": f"You've been invited to {facility_name} on IndexField",
                    "html": body_html
                },
                timeout=10.0
            )
    except Exception as e:
        print(f"[WARN] Email send failed (non-blocking): {e}")


class FacilitySetupRequest(BaseModel):
    """Request model for facility setup."""
    facility_name: str
    location: str
    technician_count: int
    industry: str
    primary_equipment: Optional[str] = None
    modules_selected: List[str] = []
    priorities: List[str] = []
    critical_asset: Optional[str] = None
    role: str


@router.post("/setup")
async def facility_setup(
    data: FacilitySetupRequest,
    context: dict = Depends(get_user_context)
):
    """
    Setup facility by writing wizard data to profiles, facilities, and facility_members.
    """
    user_id = context["user_id"]
    
    try:
        # 1. Create or get facility record in facilities table
        # Check if the user already has a current facility ID
        profile = context.get("profile") or {}
        facility_id = profile.get("current_facility_id")
        
        if not facility_id:
            # Check if user owns a facility with the same name
            existing_fac = supabase.table("facilities").select("id").eq("name", data.facility_name).eq("owner_id", user_id).execute()
            if existing_fac.data and len(existing_fac.data) > 0:
                facility_id = existing_fac.data[0]["id"]
            else:
                facility_id = str(uuid.uuid4())
                session_expires_at = datetime.now() + timedelta(days=365)
                facility_record = {
                    "id": facility_id,
                    "name": data.facility_name,
                    "location": data.location,
                    "industry": data.industry,
                    "technician_count": data.technician_count,
                    "critical_asset": data.critical_asset,
                    "modules_selected": data.modules_selected,
                    "priorities": data.priorities,
                    "primary_equipment": data.primary_equipment,
                    "account_type": "sandbox",
                    "query_count": 0,
                    "session_expires_at": session_expires_at.isoformat(),
                    "converted": False,
                    "setup_complete": True,
                    "health_score": 75,
                    "owner_id": user_id,
                    "created_at": datetime.now().isoformat()
                }
                supabase.table("facilities").insert(facility_record).execute()
        else:
            # Update the existing facility details
            supabase.table("facilities").update({
                "name": data.facility_name,
                "location": data.location,
                "industry": data.industry,
                "technician_count": data.technician_count,
                "critical_asset": data.critical_asset,
                "modules_selected": data.modules_selected,
                "priorities": data.priorities,
                "primary_equipment": data.primary_equipment,
                "setup_complete": True
            }).eq("id", facility_id).execute()

        # 2. Add current user to facility_members if not exists
        member_check = supabase.table("facility_members").select("*").eq("facility_id", facility_id).eq("user_id", user_id).execute()
        if not member_check.data or len(member_check.data) == 0:
            member_record = {
                "id": str(uuid.uuid4()),
                "facility_id": facility_id,
                "user_id": user_id,
                "role": data.role,
                "status": "active",
                "joined_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            supabase.table("facility_members").insert(member_record).execute()
        else:
            # Update role and status
            supabase.table("facility_members").update({
                "role": data.role,
                "status": "active"
            }).eq("facility_id", facility_id).eq("user_id", user_id).execute()

        # 3. Upsert / update user profile in profiles table
        profile_update = {
            "current_facility_id": facility_id,
            "role": data.role,
            "setup_complete": True,
            "facility_name": data.facility_name,
            "location": data.location,
            "technician_count": data.technician_count,
            "industry": data.industry,
            "primary_equipment": data.primary_equipment,
            "modules_selected": data.modules_selected,
            "priorities": data.priorities,
            "critical_asset": data.critical_asset,
            "updated_at": datetime.now().isoformat()
        }
        
        # Check if profile exists
        prof_check = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if prof_check.data and len(prof_check.data) > 0:
            profile_response = supabase.table("profiles").update(profile_update).eq("id", user_id).execute()
        else:
            profile_update["id"] = user_id
            profile_update["created_at"] = datetime.now().isoformat()
            profile_response = supabase.table("profiles").insert(profile_update).execute()
            
        return profile_response.data[0] if profile_response.data else {}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("FACILITY_SETUP_FAILED", "Failed to setup facility node", str(e))
        )


class FacilityCreateRequest(BaseModel):
    """Request model for creating a facility."""
    name: str
    location: Optional[str] = None
    industry: str
    technician_count: int = 1
    critical_asset: Optional[str] = None
    modules_selected: List[str] = []
    priorities: List[str] = []
    primary_equipment: Optional[str] = None


class FacilityResponse(BaseModel):
    """Response model for facility data."""
    id: str
    name: str
    location: Optional[str]
    industry: str
    technician_count: int
    critical_asset: Optional[str]
    modules_selected: List[str]
    priorities: List[str]
    primary_equipment: Optional[str]
    account_type: str
    query_count: int
    session_expires_at: Optional[str]
    converted: bool
    setup_complete: bool
    health_score: int
    created_at: str


@router.post("/create", response_model=FacilityResponse)
async def create_facility(
    facility_data: FacilityCreateRequest,
    context: dict = Depends(get_user_context)
):
    """
    Create a new facility for the user.
    This is called after the setup wizard is completed.
    """
    user_id = context["user_id"]
    
    try:
        # Check if user already has a facility
        profile_response = supabase.table("profiles").select("current_facility_id").eq("id", user_id).single()
        
        if profile_response.data and profile_response.data.get("current_facility_id"):
            raise HTTPException(
                status_code=400,
                detail="User already has a facility"
            )
        
        # Create facility
        facility_id = str(uuid.uuid4())
        session_expires_at = datetime.now() + timedelta(hours=24)
        
        facility_record = {
            "id": facility_id,
            "name": facility_data.name,
            "location": facility_data.location,
            "industry": facility_data.industry,
            "technician_count": facility_data.technician_count,
            "critical_asset": facility_data.critical_asset,
            "modules_selected": facility_data.modules_selected,
            "priorities": facility_data.priorities,
            "primary_equipment": facility_data.primary_equipment,
            "account_type": "sandbox",
            "query_count": 0,
            "session_expires_at": session_expires_at.isoformat(),
            "converted": False,
            "setup_complete": True,
            "health_score": 75,  # Initial health score
            "owner_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
        facility_response = supabase.table("facilities").insert(facility_record).execute()
        
        if not facility_response.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create facility"
            )
        
        # Create facility member record for owner
        member_record = {
            "id": str(uuid.uuid4()),
            "facility_id": facility_id,
            "user_id": user_id,
            "role": "owner",
            "status": "active",
            "joined_at": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("facility_members").insert(member_record).execute()
        
        # Update user's current facility
        supabase.table("profiles").update({
            "current_facility_id": facility_id,
            "updated_at": datetime.now().isoformat()
        }).eq("id", user_id).execute()
        
        return FacilityResponse(**facility_record)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("FACILITY_CREATE_FAILED", "Failed to create facility", str(e))
        )


@router.get("/current", response_model=FacilityResponse)
async def get_current_facility(context: dict = Depends(get_user_context)):
    """Get the user's current facility."""
    facility = context.get("facility")
    
    if not facility:
        raise HTTPException(
            status_code=404,
            detail="No facility found for user"
        )
    
    return FacilityResponse(**facility)


@router.patch("/update")
async def update_facility(
    facility_data: Dict[str, Any],
    context: dict = Depends(require_ownership)
):
    """
    Update facility information.
    Only owners can update facility details.
    """
    facility_id = context["facility_id"]
    
    try:
        # Build update dict with only allowed fields
        allowed_fields = [
            "name", "location", "industry", "technician_count",
            "critical_asset", "modules_selected", "priorities",
            "primary_equipment"
        ]
        
        update_data = {k: v for k, v in facility_data.items() if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No valid fields to update"
            )
        
        supabase.table("facilities").update(update_data).eq("id", facility_id).execute()
        
        return {"success": True, "message": "Facility updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("FACILITY_UPDATE_FAILED", "Failed to update facility", str(e))
        )


@router.get("/health")
async def get_facility_health(context: dict = Depends(get_user_context)):
    """Get facility health score and breakdown."""
    facility = context.get("facility")
    # If no facility (demo user), return default health summary
    if not facility:
        return {
            "health_score": 0,
            "breakdown": {"documents": 0, "asset_coverage": 0, "maintenance": 0, "work_orders": 0, "activity": 0},
            "top_issues": []
        }
    
    # TODO: Calculate actual health metrics from data
    health_score = facility.get("health_score", 0)
    
    # Health breakdown (placeholder values)
    breakdown = {
        "documents": 80,
        "asset_coverage": 70,
        "maintenance": 75,
        "work_orders": 85,
        "activity": 90
    }
    
    # Top issues (placeholder)
    top_issues = [
        {
            "id": "1",
            "title": "Overdue maintenance on Hydraulic Press #3",
            "severity": "high",
            "category": "maintenance"
        }
    ]
    
    return {
        "health_score": health_score,
        "breakdown": breakdown,
        "top_issues": top_issues
    }


class InviteAcceptRequest(BaseModel):
    """Request model for accepting an invite."""
    token: str


@router.post("/accept-invite")
async def accept_invite(
    invite_data: InviteAcceptRequest,
    context: dict = Depends(get_user_context)
):
    """
    Accept a facility invitation.
    Activates the facility_members record and sets current_facility_id.
    """
    user_id = context["user_id"]
    
    try:
        # Find the pending invite
        member_response = supabase.table("facility_members").select("*").eq(
            "invite_token", invite_data.token
        ).eq("status", "pending").single()
        
        if not member_response.data:
            raise HTTPException(
                status_code=404,
                detail="Invalid or expired invite token"
            )
        
        member = member_response.data
        facility_id = member["facility_id"]
        
        # Update member record
        supabase.table("facility_members").update({
            "status": "active",
            "user_id": user_id,  # Now linked to actual user
            "joined_at": datetime.now().isoformat()
        }).eq("id", member["id"]).execute()
        
        # Update user's current facility
        supabase.table("profiles").update({
            "current_facility_id": facility_id,
            "updated_at": datetime.now().isoformat()
        }).eq("id", user_id).execute()
        
        return {"success": True, "message": "Invite accepted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("INVITE_ACCEPT_FAILED", "Failed to accept invite", str(e))
        )


# ============================================
# TEAM MANAGEMENT ROUTES
# ============================================

@router.get("/members")
async def get_facility_members(context: dict = Depends(get_user_context)):
    """Get all members of the current user's facility."""
    user_id = context["user_id"]
    facility = context.get("facility") or {}
    facility_id = facility.get("id")
    
    if not facility_id:
       raise HTTPException(
           status_code=400,
           detail="User does not have an active facility"
       )
    
    try:
       # Get all members with their profile info
       members_response = supabase.table("facility_members").select(
           "id, user_id, role, status, joined_at, created_at"
       ).eq("facility_id", facility_id).execute()
        
       members = []
       for member in members_response.data:
           # Get profile info
           profile_response = supabase.table("profiles").select(
               "full_name, email, last_sign_in_at"
           ).eq("id", member["user_id"]).execute()
            
           profile = profile_response.data[0] if profile_response.data else {}
           members.append({
               "user_id": member["user_id"],
               "name": profile.get("full_name", "Unknown"),
               "email": profile.get("email", ""),
               "role": member["role"],
               "status": member["status"],
               "joined": member.get("joined_at", member.get("created_at")),
               "last_active": profile.get("last_sign_in_at")
           })
        
       return {"members": members}
        
    except Exception as e:
       raise HTTPException(
           status_code=500,
           detail=format_error_response("GET_MEMBERS_FAILED", "Failed to get facility members", str(e))
       )


class InviteRequest(BaseModel):
    """Request model for sending invites."""
    invited_email: str
    role: str
    personal_message: Optional[str] = None


@router.post("/invite")
async def send_team_invite(
    data: InviteRequest,
    context: dict = Depends(get_user_context)
):
    """Send an invite to join the facility."""
    user_id = context["user_id"]
    facility = context.get("facility") or {}
    facility_id = facility.get("id")
    role = context.get("role")
    
    # Only owner/plant_manager can invite
    if role not in ["owner", "plant_manager", "admin"]:
       raise HTTPException(
           status_code=403,
           detail="Only admins can send invites"
       )
    
    if not facility_id:
       raise HTTPException(
           status_code=400,
           detail="User does not have an active facility"
       )
    
    try:
       invite_token = str(uuid.uuid4())
       expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        
       # Create invite record
       invite_record = {
           "id": str(uuid.uuid4()),
           "facility_id": facility_id,
           "invited_email": data.invited_email,
           "role": data.role,
           "token": invite_token,
           "expires_at": expires_at,
           "invited_by": user_id,
           "accepted": False,
           "created_at": datetime.now().isoformat()
       }
        
       supabase.table("facility_invites").insert(invite_record).execute()
        
       # Get inviter name for the email
       inviter_name = context.get("profile", {}).get("full_name") or "Your administrator"
       facility_name = facility.get("name", "your facility")
       
       # Send invite email via Resend (non-blocking — skips if no key configured)
       await send_invite_email(
           to_email=data.invited_email,
           facility_name=facility_name,
           role=data.role,
           inviter_name=inviter_name,
           token=invite_token,
           personal_message=data.personal_message
       )
        
       return {
           "success": True,
           "message": f"Invite sent to {data.invited_email}",
           "token": invite_token
       }

    except Exception as e:
       raise HTTPException(
           status_code=500,
           detail=format_error_response("INVITE_SEND_FAILED", "Failed to send invite", str(e))
       )


@router.get("/invites")
async def get_pending_invites(context: dict = Depends(get_user_context)):
    """Get all pending invites for the facility."""
    user_id = context["user_id"]
    facility = context.get("facility") or {}
    facility_id = facility.get("id")
    role = context.get("role")
    
    # Only owner/plant_manager can view invites
    if role not in ["owner", "plant_manager", "admin"]:
       raise HTTPException(
           status_code=403,
           detail="Only admins can view invites"
       )
    
    if not facility_id:
       raise HTTPException(
           status_code=400,
           detail="User does not have an active facility"
       )
    
    try:
       invites_response = supabase.table("facility_invites").select(
           "id, invited_email, role, token, expires_at, invited_by, created_at"
       ).eq("facility_id", facility_id).eq("accepted", False).execute()
        
       invites = []
       for invite in invites_response.data:
           # Get inviter name
           inviter_response = supabase.table("profiles").select("full_name").eq("id", invite["invited_by"]).execute()
           inviter_name = inviter_response.data[0]["full_name"] if inviter_response.data else "Unknown"
            
           invites.append({
               "id": invite["id"],
               "email": invite["invited_email"],
               "role": invite["role"],
               "sent_at": invite.get("created_at"),
               "invited_by": inviter_name
           })
        
       return {"invites": invites}
        
    except Exception as e:
       raise HTTPException(
           status_code=500,
           detail=format_error_response("GET_INVITES_FAILED", "Failed to get invites", str(e))
       )


@router.delete("/invites/{invite_id}")
async def cancel_invite(
    invite_id: str,
    context: dict = Depends(get_user_context)
):
    """Cancel a pending invite."""
    user_id = context["user_id"]
    role = context.get("role")
    
    # Only owner can cancel invites
    if role not in ["owner", "plant_manager", "admin"]:
       raise HTTPException(
           status_code=403,
           detail="Only admins can cancel invites"
       )
    
    try:
       supabase.table("facility_invites").delete().eq("id", invite_id).execute()
       return {"success": True, "message": "Invite cancelled"}
        
    except Exception as e:
       raise HTTPException(
           status_code=500,
           detail=format_error_response("CANCEL_INVITE_FAILED", "Failed to cancel invite", str(e))
       )


class RoleChangeRequest(BaseModel):
    """Request model for changing a member's role."""
    role: str


@router.patch("/members/{user_id}/role")
async def change_member_role(
    user_id: str,
    body: RoleChangeRequest,
    context: dict = Depends(get_user_context)
):
    """Change a member's role."""
    current_user_id = context["user_id"]
    current_role = context.get("role")
    facility = context.get("facility") or {}
    facility_id = facility.get("id")
    role = body.role
    
    # Only owner can change roles
    if current_role not in ["owner", "plant_manager", "admin"]:
       raise HTTPException(
           status_code=403,
           detail="Only admins can change member roles"
       )
    
    # Cannot change own role
    if user_id == current_user_id:
       raise HTTPException(
           status_code=400,
           detail="Cannot change your own role"
       )
    
    if not facility_id:
       raise HTTPException(
           status_code=400,
           detail="User does not have an active facility"
       )
    
    try:
       supabase.table("facility_members").update({
           "role": role
       }).eq("facility_id", facility_id).eq("user_id", user_id).execute()
        
       return {"success": True, "message": f"Member role changed to {role}"}
        
    except Exception as e:
       raise HTTPException(
           status_code=500,
           detail=format_error_response("CHANGE_ROLE_FAILED", "Failed to change role", str(e))
       )


class InviteAcceptPublicRequest(BaseModel):
    """Request model for publicly accepting an invite via token."""
    token: str


@router.post("/invite/accept")
async def accept_invite_public(data: InviteAcceptPublicRequest):
    """
    Public route — accepts an invite using the token from the email link.
    Validates token, marks invite as accepted.
    Redirects to signin page with success param.
    """
    try:
        # Find the pending invite
        invite_response = supabase.table("facility_invites").select("*").eq(
            "token", data.token
        ).eq("accepted", False).execute()
        
        if not invite_response.data or len(invite_response.data) == 0:
            raise HTTPException(
                status_code=404,
                detail="Invalid or expired invite token"
            )
        
        invite = invite_response.data[0]
        
        # Check expiry
        expires_at = invite.get("expires_at")
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now().astimezone() > exp_dt:
                    raise HTTPException(
                        status_code=410,
                        detail="This invite has expired. Please ask for a new invite."
                    )
            except ValueError:
                pass  # If we can't parse, allow it through
        
        # Mark as accepted so the setup wizard can proceed
        supabase.table("facility_invites").update({
            "accepted": True,
            "accepted_at": datetime.now().isoformat()
        }).eq("id", invite["id"]).execute()
        
        # Get facility info for context
        facility_response = supabase.table("facilities").select(
            "id, name, industry"
        ).eq("id", invite["facility_id"]).execute()
        
        facility_name = ""
        if facility_response.data:
            facility_name = facility_response.data[0].get("name", "")
        
        return {
            "success": True,
            "message": f"Invite accepted. Please sign in to join {facility_name}.",
            "facility_name": facility_name,
            "role": invite["role"],
            "facility_id": invite["facility_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("INVITE_ACCEPT_FAILED", "Failed to accept invite", str(e))
        )


@router.delete("/members/{user_id}")
async def remove_facility_member(
    user_id: str,
    context: dict = Depends(get_user_context)
):
    """Remove a member from the facility."""
    current_user_id = context["user_id"]
    current_role = context.get("role")
    facility = context.get("facility") or {}
    facility_id = facility.get("id")
    
    # Only owner can remove members
    if current_role not in ["owner", "plant_manager", "admin"]:
       raise HTTPException(
           status_code=403,
           detail="Only admins can remove members"
       )
    
    # Cannot remove self
    if user_id == current_user_id:
       raise HTTPException(
           status_code=400,
           detail="Cannot remove yourself from the facility"
       )
    
    if not facility_id:
       raise HTTPException(
           status_code=400,
           detail="User does not have an active facility"
       )
    
    try:
       supabase.table("facility_members").delete().eq(
           "facility_id", facility_id
       ).eq("user_id", user_id).execute()
        
       return {"success": True, "message": "Member removed from facility"}
        
    except Exception as e:
       raise HTTPException(
           status_code=500,
           detail=format_error_response("REMOVE_MEMBER_FAILED", "Failed to remove member", str(e))
       )
