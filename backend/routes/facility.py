from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client
from config import settings

router = APIRouter()
security = HTTPBearer()

class HealthScoreBreakdown(BaseModel):
    score: int
    max: int
    label: str
    detail: str

class FacilityHealthResponse(BaseModel):
    score: int
    status: str
    breakdown: Dict[str, HealthScoreBreakdown]
    top_issues: List[str]
    calculated_at: str

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

@router.get("/api/facility/health", response_model=FacilityHealthResponse)
async def get_facility_health(current_user: dict = Depends(get_current_user)):
    """Calculate facility health score from real data."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Get user profile for facility name
        profile_response = supabase.table('profiles').select('facility_name').eq('id', current_user['user_id']).execute()
        facility_name = profile_response.data[0].get('facility_name', 'Default Facility') if profile_response.data else 'Default Facility'
        
        # Fetch all relevant data
        manuals_response = supabase.table('user_manuals').select('*').eq('user_id', current_user['user_id']).execute()
        assets_response = supabase.table('user_assets').select('*').eq('user_id', current_user['user_id']).execute()
        work_orders_response = supabase.table('work_orders').select('*').eq('user_id', current_user['user_id']).execute()
        tribal_response = supabase.table('tribal_knowledge').select('*').eq('user_id', current_user['user_id']).execute()
        handovers_response = supabase.table('shift_handovers').select('*').eq('user_id', current_user['user_id']).execute()
        query_history_response = supabase.table('query_history').select('*').eq('user_id', current_user['user_id']).execute()
        
        manuals = manuals_response.data
        assets = assets_response.data
        work_orders = work_orders_response.data
        tribal_knowledge = tribal_response.data
        handovers = handovers_response.data
        query_history = query_history_response.data
        
        top_issues = []
        
        # 1. Documents Score (20 points)
        # Points = (manuals_uploaded / estimated_total_assets) × 20
        # For now, estimate total assets as max(assets_count, 10)
        total_assets_estimate = max(len(assets), 10)
        documents_score = min(int((len(manuals) / total_assets_estimate) * 20), 20)
        if len(manuals) < len(assets):
            top_issues.append(f"{len(assets) - len(manuals)} assets have no linked manuals")
        
        # 2. Asset Documentation Score (20 points)
        # Points = (assets_with_linked_manuals / total_assets) × 20
        assets_with_manuals = len([a for a in assets if a.get('manual_ids') and len(a['manual_ids']) > 0])
        asset_doc_score = int((assets_with_manuals / max(len(assets), 1)) * 20) if assets else 0
        
        # 3. Maintenance Score (20 points)
        # No overdue items = 20 points, deduct 2 per overdue item
        overdue_maintenance = 0
        for asset in assets:
            if asset.get('next_maint'):
                try:
                    next_maint = datetime.fromisoformat(asset['next_maint'].replace('Z', '+00:00'))
                    if next_maint < datetime.now():
                        overdue_maintenance += 1
                        top_issues.append(f"Maintenance overdue on {asset.get('name', 'Unknown asset')}")
                except:
                    pass
        maintenance_score = max(20 - (overdue_maintenance * 2), 0)
        
        # 4. Work Order Score (20 points)
        # No critical open orders = 20 points, deduct 5 per critical, 2 per high
        critical_open = len([wo for wo in work_orders if wo['priority'] == 'CRITICAL' and wo['status'] in ['OPEN', 'IN_PROGRESS']])
        high_open = len([wo for wo in work_orders if wo['priority'] == 'HIGH' and wo['status'] in ['OPEN', 'IN_PROGRESS']])
        work_order_score = max(20 - (critical_open * 5) - (high_open * 2), 0)
        if critical_open > 0:
            top_issues.append(f"{critical_open} critical work orders open")
        if high_open > 0:
            top_issues.append(f"{high_open} high-priority work orders open")
        
        # 5. Activity Score (20 points)
        # Queries in last 7 days > 0 = 10 points
        # Tribal knowledge entries > 0 = 5 points
        # Handover generated this week = 5 points
        week_ago = datetime.now() - timedelta(days=7)
        recent_queries = len([q for q in query_history if datetime.fromisoformat(q['created_at'].replace('Z', '+00:00')) > week_ago])
        tribal_count = len(tribal_knowledge)
        recent_handovers = len([h for h in handovers if datetime.fromisoformat(h['created_at'].replace('Z', '+00:00')) > week_ago])
        
        activity_score = 0
        if recent_queries > 0:
            activity_score += 10
        else:
            top_issues.append("No queries logged in 7 days")
        
        if tribal_count > 0:
            activity_score += 5
        
        if recent_handovers > 0:
            activity_score += 5
        
        # Calculate total score
        total_score = documents_score + asset_doc_score + maintenance_score + work_order_score + activity_score
        
        # Determine status
        if total_score >= 80:
            status = "GREEN"
        elif total_score >= 60:
            status = "AMBER"
        else:
            status = "RED"
        
        # Build breakdown
        breakdown = {
            "documents": HealthScoreBreakdown(
                score=documents_score,
                max=20,
                label="Documents",
                detail=f"{len(manuals)} manuals uploaded"
            ),
            "asset_documentation": HealthScoreBreakdown(
                score=asset_doc_score,
                max=20,
                label="Asset Coverage",
                detail=f"{assets_with_manuals}/{len(assets)} assets with manuals"
            ),
            "maintenance": HealthScoreBreakdown(
                score=maintenance_score,
                max=20,
                label="Maintenance",
                detail=f"{overdue_maintenance} overdue items"
            ),
            "work_orders": HealthScoreBreakdown(
                score=work_order_score,
                max=20,
                label="Work Orders",
                detail=f"{critical_open} critical, {high_open} high priority open"
            ),
            "activity": HealthScoreBreakdown(
                score=activity_score,
                max=20,
                label="Platform Activity",
                detail=f"{recent_queries} queries, {tribal_count} tribal entries, {recent_handovers} handovers this week"
            )
        }
        
        return FacilityHealthResponse(
            score=total_score,
            status=status,
            breakdown=breakdown,
            top_issues=top_issues[:5],  # Limit to top 5 issues
            calculated_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate facility health: {str(e)}")
