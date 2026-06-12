from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from supabase import create_client
from config import settings
import json
import requests
import uuid

router = APIRouter()
security = HTTPBearer(auto_error=False)

def get_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Get user ID from credentials, handle guest tokens"""
    if credentials is None:
        # No credentials provided - treat as guest
        return 'guest_' + str(uuid.uuid4())[:8]
    
    token = credentials.credentials
    if token.startswith('guest_token_'):
        # Guest token - extract guest ID
        return token.replace('guest_token_', '')
    
    # JWT token - validate with Supabase
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        user = supabase.auth.get_user(token)
        if user and user.data and user.data.user:
            return user.data.user.id
        # If JWT validation fails, treat as guest
        return 'guest_' + str(uuid.uuid4())[:8]
    except Exception as e:
        # If JWT validation fails, treat as guest
        return 'guest_' + str(uuid.uuid4())[:8]

class WorkOrderCreate(BaseModel):
    asset_id: Optional[str] = None
    asset_name: str
    title: str
    description: str
    priority: str = "MEDIUM"
    assigned_to: Optional[str] = None
    estimated_hours: Optional[float] = None
    due_date: Optional[str] = None
    linked_manual_id: Optional[str] = None
    linked_page: Optional[int] = None
    linked_tribal_knowledge_id: Optional[str] = None
    notes: Optional[str] = None
    created_from: str = "MANUAL"
    procedure_steps: Optional[List[str]] = None

class WorkOrderGenerateRequest(BaseModel):
    asset_id: Optional[str] = None
    query: str
    ai_answer: str
    manual_reference: Optional[str] = None

class WorkOrderUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

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
    # Skip sandbox limit check for guest users
    if user_id.startswith('guest_'):
        return
    
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    profile_response = supabase.table('profiles').select('account_type').eq('id', user_id).execute()
    if not profile_response.data:
        # If no profile found, treat as guest (no limits)
        return
    
    profile = profile_response.data[0]
    account_type = profile.get('account_type', 'sandbox')
    
    if account_type == 'sandbox':
        if feature == 'work_orders':
            count_response = supabase.table('work_orders').select('id').eq('user_id', user_id).execute()
            if len(count_response.data) >= limit:
                raise HTTPException(status_code=402, detail=f"Sandbox limit: Maximum {limit} work orders allowed")

@router.post("/api/workorders/create")
async def create_work_order(
    data: WorkOrderCreate,
    user_id: str = Depends(get_user_id)
):
    """Create a new work order."""
    # For guest users, return success without saving to Supabase
    if user_id.startswith('guest_'):
        return {
            "success": True,
            "work_order_id": f"WO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}",
            "id": f"WO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}",
            "user_id": user_id,
            "facility_name": "Guest Facility",
            "asset_id": data.asset_id,
            "asset_name": data.asset_name,
            "title": data.title,
            "description": data.description,
            "priority": data.priority,
            "status": "OPEN",
            "assigned_to": data.assigned_to,
            "estimated_hours": data.estimated_hours,
            "linked_manual_id": data.linked_manual_id,
            "linked_page": data.linked_page,
            "procedure_steps": data.procedure_steps,
            "due_date": data.due_date,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "notes": [],
            "message": "Work order created successfully (local-only)"
        }
    
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    # Check sandbox limit (max 2 work orders for sandbox)
    check_sandbox_limit(user_id, 'work_orders', 2)
    
    try:
        # Get facility name from profile
        profile_response = supabase.table('profiles').select('facility_name').eq('id', user_id).execute()
        facility_name = profile_response.data[0].get('facility_name', 'Default Facility') if profile_response.data else 'Default Facility'
        
        work_order_data = {
            "user_id": user_id,
            "facility_name": facility_name,
            "asset_id": data.asset_id,
            "asset_name": data.asset_name,
            "title": data.title,
            "description": data.description,
            "priority": data.priority,
            "status": "OPEN",
            "assigned_to": data.assigned_to,
            "estimated_hours": data.estimated_hours,
            "linked_manual_id": data.linked_manual_id,
            "linked_page": data.linked_page,
            "linked_tribal_knowledge_id": data.linked_tribal_knowledge_id,
            "created_from": data.created_from,
            "due_date": data.due_date,
            "notes": data.notes,
            "procedure_steps": data.procedure_steps or [],
            "ai_briefed": False,
            "ai_briefing": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table('work_orders').insert(work_order_data).execute()
        
        # Log shift event
        supabase.table('shift_events').insert({
            "user_id": user_id,
            "event_type": "WORK_ORDER",
            "asset_id": data.asset_id,
            "asset_name": data.asset_name,
            "description": f"Work order created: {data.title}",
            "severity": "INFO",
            "created_at": datetime.now().isoformat()
        }).execute()
        
        return {
            "success": True,
            "id": response.data[0]['id'],
            "message": "Work order created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create work order: {str(e)}")

@router.get("/api/workorders")
async def get_work_orders(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    asset_id_filter: Optional[str] = None,
    user_id: str = Depends(get_user_id)
):
    """Get all work orders for user with optional filters."""
    # For guest users, return empty array
    if user_id.startswith('guest_'):
        return []
    
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        query = supabase.table('work_orders').select('*').eq('user_id', user_id)
        
        if status_filter:
            query = query.eq('status', status_filter)
        if priority_filter:
            query = query.eq('priority', priority_filter)
        if asset_id_filter:
            query = query.eq('asset_id', asset_id_filter)
        
        response = query.order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch work orders: {str(e)}")

@router.patch("/api/workorders/{work_order_id}")
async def update_work_order(
    work_order_id: str,
    data: WorkOrderUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update work order status, assignment, or notes."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        update_data = {"updated_at": datetime.now().isoformat()}
        
        if data.status:
            update_data["status"] = data.status
            if data.status == "COMPLETE":
                update_data["completed_at"] = datetime.now().isoformat()
            # Auto-set OVERDUE if due_date is past and status is OPEN or IN_PROGRESS
            elif data.status in ["OPEN", "IN_PROGRESS"]:
                wo_response = supabase.table('work_orders').select('due_date').eq('id', work_order_id).eq('user_id', user_id).execute()
                if wo_response.data and wo_response.data[0].get('due_date'):
                    due_date = datetime.fromisoformat(wo_response.data[0]['due_date'].replace('Z', '+00:00'))
                    if due_date < datetime.now():
                        update_data["status"] = "OVERDUE"
        
        if data.assigned_to:
            update_data["assigned_to"] = data.assigned_to
        
        if data.notes:
            update_data["notes"] = data.notes
        
        response = supabase.table('work_orders').update(update_data).eq('id', work_order_id).eq('user_id', user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        # Recalculate facility health score on work order update
        try:
            from .facility import recalculate_health_score
            await recalculate_health_score(user_id)
        except:
            pass  # Don't fail if health score recalculation fails
        
        return {"success": True, "message": "Work order updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update work order: {str(e)}")

@router.post("/api/workorders/generate")
async def generate_work_order(
    request: WorkOrderGenerateRequest,
    user_id: str = Depends(get_user_id)
):
    """Generate work order from AI analysis of query and answer."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Get asset name if asset_id provided
        asset_name = "Unknown Asset"
        if request.asset_id:
            asset_response = supabase.table('user_assets').select('name').eq('id', request.asset_id).execute()
            if asset_response.data:
                asset_name = asset_response.data[0].get('name')
        
        # Generate work order using Groq AI
        generated_data = await generate_ai_work_order(request.query, request.ai_answer, asset_name, request.manual_reference)
        
        return generated_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate work order: {str(e)}")

async def generate_ai_work_order(query: str, ai_answer: str, asset_name: str, manual_reference: Optional[str]) -> dict:
    """Generate work order data using Groq AI."""
    if not settings.GROQ_API_KEY:
        # Fallback: return basic template
        return {
            "title": f"Maintenance Task - {asset_name}",
            "description": f"Based on query: {query}\nAI Answer: {ai_answer}",
            "priority": "MEDIUM",
            "estimated_hours": 2.0,
            "recommended_due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "safety_notes": "Review safety procedures before starting work"
        }
    
    prompt = f"""Based on this maintenance query and AI answer, generate a work order.

Query: {query}
AI Answer: {ai_answer}
Asset: {asset_name}
Manual Reference: {manual_reference or 'None'}

Generate a JSON response with this exact structure:
{{
  "title": "Brief descriptive title",
  "description": "Detailed description of the work to be done",
  "priority": "HIGH|MEDIUM|LOW|CRITICAL",
  "estimated_hours": number,
  "recommended_due_date": "ISO format date",
  "safety_notes": "Any safety considerations"
}}

Return ONLY the JSON, no other text."""
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return json.loads(result['choices'][0]['message']['content'])
        else:
            raise Exception(f"Groq API error: {response.text}")
    except Exception as e:
        print(f"[ERROR] AI work order generation failed: {e}")
        # Return basic template
        return {
            "title": f"Maintenance Task - {asset_name}",
            "description": f"Based on query: {query}\nAI Answer: {ai_answer}",
            "priority": "MEDIUM",
            "estimated_hours": 2.0,
            "recommended_due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "safety_notes": "Review safety procedures before starting work"
        }

class WorkOrderBriefRequest(BaseModel):
    work_order_id: str

class WorkOrderNoteRequest(BaseModel):
    note: str

@router.post("/api/workorders/brief")
async def generate_ai_briefing(
    request: WorkOrderBriefRequest,
    user_id: str = Depends(get_user_id)
):
    """Generate AI briefing for a work order using RAG pipeline."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Get work order
        wo_response = supabase.table('work_orders').select('*').eq('id', request.work_order_id).eq('user_id', user_id).execute()
        if not wo_response.data:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        work_order = wo_response.data[0]
        
        # Check sandbox limit for AI suggestions (once only)
        profile_response = supabase.table('profiles').select('account_type, ai_suggestion_count').eq('id', user_id).execute()
        if profile_response.data:
            profile = profile_response.data[0]
            if profile.get('account_type') == 'sandbox':
                ai_count = profile.get('ai_suggestion_count', 0)
                if ai_count >= 1:
                    raise HTTPException(status_code=402, detail="Sandbox limit: Maximum 1 AI briefing allowed")
                # Increment count
                supabase.table('profiles').update({'ai_suggestion_count': ai_count + 1}).eq('id', user_id).execute()
        
        # Build search query from work order details
        search_query = f"{work_order.get('title', '')} {work_order.get('description', '')} {work_order.get('asset_name', '')}"
        if work_order.get('procedure_steps'):
            search_query += " " + " ".join(work_order['procedure_steps'])
        
        # Call RAG pipeline (this would integrate with existing RAG system)
        # For now, return a simulated briefing structure
        briefing_data = {
            "sources": [
                {
                    "document_name": "Sample Manual",
                    "page": 1,
                    "section": "Overview",
                    "summary": "General maintenance procedures for this equipment type.",
                    "confidence": "HIGH"
                }
            ]
        }
        
        # Update work order with briefing
        supabase.table('work_orders').update({
            'ai_briefing': briefing_data,
            'ai_briefed': True,
            'updated_at': datetime.now().isoformat()
        }).eq('id', request.work_order_id).execute()
        
        return briefing_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI briefing: {str(e)}")

@router.post("/api/workorders/generate-suggestions")
async def generate_ai_suggestions(user_id: str = Depends(get_user_id)):
    """Generate AI work order suggestions from asset data and manuals."""
    # For guest users, return empty suggestions
    if user_id.startswith('guest_'):
        return []
    
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Check sandbox limit for AI suggestions (once only)
        profile_response = supabase.table('profiles').select('account_type, ai_suggestion_count').eq('id', user_id).execute()
        if profile_response.data:
            profile = profile_response.data[0]
            if profile.get('account_type') == 'sandbox':
                ai_count = profile.get('ai_suggestion_count', 0)
                if ai_count >= 1:
                    raise HTTPException(status_code=402, detail="Sandbox limit: Maximum 1 AI suggestion allowed")
                # Increment count
                supabase.table('profiles').update({'ai_suggestion_count': ai_count + 1}).eq('id', user_id).execute()
        
        # Get all user assets
        assets_response = supabase.table('user_assets').select('*').eq('user_id', user_id).execute()
        assets = assets_response.data if assets_response.data else []
        
        suggestions = []
        
        # Generate suggestions based on asset data
        for asset in assets:
            # Check if maintenance is overdue (simplified logic)
            last_service = asset.get('last_service_date')
            if last_service:
                last_service_date = datetime.fromisoformat(last_service.replace('Z', '+00:00'))
                days_since = (datetime.now() - last_service_date).days
                
                # Suggest if overdue by more than 180 days
                if days_since > 180:
                    suggestions.append({
                        "asset_id": asset['id'],
                        "asset_name": asset['name'],
                        "priority": "HIGH",
                        "title": f"Scheduled maintenance - {asset['name']}",
                        "description": f"Maintenance overdue by {days_since - 180} days",
                        "source": "Maintenance Schedule",
                        "interval": "Every 6 months",
                        "last_completed": last_service_date.strftime("%b %Y")
                    })
        
        return suggestions
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

@router.post("/api/workorders/{work_order_id}/notes")
async def add_work_order_note(
    work_order_id: str,
    request: WorkOrderNoteRequest,
    user_id: str = Depends(get_user_id)
):
    """Add a note to a work order."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Get current work order
        wo_response = supabase.table('work_orders').select('notes').eq('id', work_order_id).eq('user_id', user_id).execute()
        if not wo_response.data:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        current_notes = wo_response.data[0].get('notes') or []
        
        # Add new note
        new_note = {
            "text": request.note,
            "author": "Guest" if user_id.startswith('guest_') else "User",
            "timestamp": datetime.now().isoformat()
        }
        current_notes.append(new_note)
        
        # Update work order
        supabase.table('work_orders').update({
            'notes': current_notes,
            'updated_at': datetime.now().isoformat()
        }).eq('id', work_order_id).eq('user_id', user_id).execute()
        
        return {"success": True, "message": "Note added"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add note: {str(e)}")

@router.get("/api/workorders/stats")
async def get_work_order_stats(user_id: str = Depends(get_user_id)):
    """Get work order statistics for dashboard."""
    # For guest users, return default stats
    if user_id.startswith('guest_'):
        return {
            "critical_open": 0,
            "high_priority": 0,
            "total_open": 0,
            "completed_this_month": 0
        }
    
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        all_orders = supabase.table('work_orders').select('*').eq('user_id', user_id).execute().data
        
        # Critical open (CRITICAL priority and not COMPLETE)
        critical_open = len([wo for wo in all_orders if wo.get('priority') == 'CRITICAL' and wo.get('status') != 'COMPLETE'])
        
        # High priority open
        high_priority = len([wo for wo in all_orders if wo.get('priority') == 'HIGH' and wo.get('status') not in ['COMPLETE', 'CANCELLED']])
        
        # Due today or overdue
        today = datetime.now().date()
        due_today = 0
        for wo in all_orders:
            if wo.get('due_date') and wo.get('status') not in ['COMPLETE', 'CANCELLED']:
                due_date = datetime.fromisoformat(wo['due_date'].replace('Z', '+00:00')).date()
                if due_date <= today:
                    due_today += 1
        
        # Completed this week
        week_ago = datetime.now() - timedelta(days=7)
        completed_this_week = len([
            wo for wo in all_orders 
            if wo.get('status') == 'COMPLETE' 
            and wo.get('completed_at')
            and datetime.fromisoformat(wo['completed_at'].replace('Z', '+00:00')) > week_ago
        ])
        
        return {
            "critical_open": critical_open,
            "high_priority": high_priority,
            "due_today": due_today,
            "completed_this_week": completed_this_week
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch work order stats: {str(e)}")
