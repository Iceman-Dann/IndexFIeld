from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from supabase import create_client
from config import settings

router = APIRouter()
security = HTTPBearer()

class TribalKnowledgeAdd(BaseModel):
    asset_id: Optional[str] = None
    manual_id: Optional[str] = None
    page_reference: Optional[int] = None
    section: Optional[str] = None
    original_query: Optional[str] = None
    ai_answer_summary: Optional[str] = None
    technician_note: str
    added_by_name: str
    voice_query: bool = False

class TribalKnowledgeResponse(BaseModel):
    id: str
    technician_note: str
    added_by_name: str
    created_at: str
    verified: bool
    helpful_count: int
    asset_name: Optional[str] = None
    manual_name: Optional[str] = None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info from Supabase."""
    from jose import jwt, JWTError
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        user_response = supabase.auth.get_user(token)
        
        return {
            "user_id": user_id,
            "token": token,
            "email": user_response.user.email if user_response.user else None
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def check_sandbox_limit(user_id: str, feature: str, limit: int):
    """Check if sandbox user has exceeded limit for a feature."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    profile_response = supabase.table('profiles').select('account_type').eq('id', user_id).execute()
    if not profile_response.data:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    profile = profile_response.data[0]
    account_type = profile.get('account_type', 'sandbox')
    
    if account_type == 'sandbox':
        if feature == 'tribal_knowledge':
            count_response = supabase.table('tribal_knowledge').select('id').eq('user_id', user_id).execute()
            if len(count_response.data) >= limit:
                raise HTTPException(status_code=402, detail=f"Sandbox limit: Maximum {limit} tribal knowledge entries allowed")

@router.post("/api/tribal/add")
async def add_tribal_knowledge(
    data: TribalKnowledgeAdd,
    current_user: dict = Depends(get_current_user)
):
    """Save tribal knowledge entry."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    # Check sandbox limit (max 3 entries for sandbox)
    check_sandbox_limit(current_user['user_id'], 'tribal_knowledge', 3)
    
    try:
        # Get facility name from profile
        profile_response = supabase.table('profiles').select('facility_name').eq('id', current_user['user_id']).execute()
        facility_id = profile_response.data[0].get('facility_name', 'default') if profile_response.data else 'default'
        
        # Get asset name if asset_id provided
        asset_name = None
        if data.asset_id:
            asset_response = supabase.table('user_assets').select('name').eq('id', data.asset_id).execute()
            if asset_response.data:
                asset_name = asset_response.data[0].get('name')
        
        # Get manual name if manual_id provided
        manual_name = None
        if data.manual_id:
            manual_response = supabase.table('user_manuals').select('filename').eq('id', data.manual_id).execute()
            if manual_response.data:
                manual_name = manual_response.data[0].get('filename')
        
        tribal_data = {
            "user_id": current_user['user_id'],
            "facility_id": facility_id,
            "asset_id": data.asset_id,
            "manual_id": data.manual_id,
            "page_reference": data.page_reference,
            "section": data.section,
            "original_query": data.original_query,
            "ai_answer_summary": data.ai_answer_summary,
            "technician_note": data.technician_note,
            "added_by_name": data.added_by_name,
            "voice_query": data.voice_query,
            "verified": False,
            "helpful_count": 0,
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table('tribal_knowledge').insert(tribal_data).execute()
        
        return {
            "success": True,
            "id": response.data[0]['id'],
            "message": "Field note saved. This will appear alongside future answers about this asset."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save tribal knowledge: {str(e)}")

@router.get("/api/tribal/asset/{asset_id}")
async def get_tribal_knowledge_for_asset(
    asset_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all tribal knowledge for a specific asset."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        response = supabase.table('tribal_knowledge').select('*').eq('asset_id', asset_id).order('helpful_count', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tribal knowledge: {str(e)}")

@router.get("/api/tribal/query-context")
async def get_tribal_knowledge_for_query(
    asset_id: Optional[str] = None,
    manual_id: Optional[str] = None,
    section: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get tribal knowledge relevant to a query context."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        query = supabase.table('tribal_knowledge').select('*').eq('user_id', current_user['user_id'])
        
        if asset_id:
            query = query.eq('asset_id', asset_id)
        if manual_id:
            query = query.eq('manual_id', manual_id)
        if section:
            query = query.eq('section', section)
        
        response = query.order('helpful_count', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tribal knowledge: {str(e)}")

@router.post("/api/tribal/{knowledge_id}/verify")
async def verify_tribal_knowledge(
    knowledge_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark tribal knowledge entry as verified by supervisor."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Check if user is admin/supervisor
        profile_response = supabase.table('profiles').select('role').eq('id', current_user['user_id']).execute()
        if not profile_response.data or profile_response.data[0].get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Only supervisors can verify tribal knowledge")
        
        response = supabase.table('tribal_knowledge').update({
            'verified': True,
            'verified_by': current_user['user_id'],
            'verified_at': datetime.now().isoformat()
        }).eq('id', knowledge_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Tribal knowledge entry not found")
        
        return {"success": True, "message": "Tribal knowledge verified"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify tribal knowledge: {str(e)}")

@router.post("/api/tribal/{knowledge_id}/helpful")
async def mark_tribal_knowledge_helpful(
    knowledge_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Increment helpful count for tribal knowledge entry."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Get current helpful count
        current_response = supabase.table('tribal_knowledge').select('helpful_count').eq('id', knowledge_id).execute()
        if not current_response.data:
            raise HTTPException(status_code=404, detail="Tribal knowledge entry not found")
        
        current_count = current_response.data[0].get('helpful_count', 0)
        
        response = supabase.table('tribal_knowledge').update({
            'helpful_count': current_count + 1
        }).eq('id', knowledge_id).execute()
        
        return {"success": True, "helpful_count": current_count + 1}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update helpful count: {str(e)}")

@router.get("/api/tribal/all")
async def get_all_tribal_knowledge(
    asset_filter: Optional[str] = None,
    manual_filter: Optional[str] = None,
    verified_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Get all tribal knowledge with optional filters."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        query = supabase.table('tribal_knowledge').select('*')
        
        if asset_filter:
            query = query.eq('asset_id', asset_filter)
        if manual_filter:
            query = query.eq('manual_id', manual_filter)
        if verified_only:
            query = query.eq('verified', True)
        
        response = query.order('helpful_count', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tribal knowledge: {str(e)}")
