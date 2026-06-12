from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from supabase import create_client
from config import settings
import json
import uuid
import requests

router = APIRouter()
security = HTTPBearer()

class HandoverGenerateRequest(BaseModel):
    shift_type: Optional[str] = None
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None

class HandoverAcknowledgeRequest(BaseModel):
    name: str

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info from Supabase."""
    from jose import jwt, JWTError
    
    try:
        token = credentials.credentials
        
        # Handle guest tokens for testing
        if token.startswith('guest_token_'):
            guest_id = token.replace('guest_token_', '')
            return {
                "user_id": guest_id,
                "token": token,
                "email": f"{guest_id}@local.guest",
                "is_guest": True
            }
        
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

def check_sandbox_limit(user_id: str, feature: str, limit: int, is_guest: bool = False):
    """Check if sandbox user has exceeded limit for a feature."""
    # Skip limit check for guest users
    if is_guest or user_id.startswith('guest_'):
        return
    
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    profile_response = supabase.table('profiles').select('account_type').eq('id', user_id).execute()
    if not profile_response.data:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    profile = profile_response.data[0]
    account_type = profile.get('account_type', 'sandbox')
    
    if account_type == 'sandbox':
        if feature == 'handover':
            count_response = supabase.table('shift_handovers').select('id').eq('user_id', user_id).execute()
            if len(count_response.data) >= limit:
                raise HTTPException(status_code=402, detail=f"Sandbox limit: Maximum {limit} handover reports allowed")

@router.post("/api/handover/generate")
async def generate_handover(
    request: HandoverGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a shift handover report from activity data."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    # Check sandbox limit (max 1 handover for sandbox)
    check_sandbox_limit(current_user['user_id'], 'handover', 1, current_user.get('is_guest', False))
    
    try:
        # Get user profile for facility name and full name
        # For guest users, use defaults
        if current_user.get('is_guest'):
            facility_name = 'Demo Facility'
            generated_by_name = 'Guest User'
        else:
            profile_response = supabase.table('profiles').select('facility_name, full_name').eq('id', current_user['user_id']).execute()
            facility_name = 'Default Facility'
            generated_by_name = 'Shift Lead'
            if profile_response.data:
                facility_name = profile_response.data[0].get('facility_name', 'Default Facility') or 'Default Facility'
                generated_by_name = profile_response.data[0].get('full_name', 'Shift Lead') or 'Shift Lead'
        
        # Calculate shift window
        local_now = datetime.now()
        tz_info = local_now.astimezone().tzinfo
        now_aware = local_now.replace(tzinfo=tz_info)

        if request.shift_start:
            shift_start = datetime.fromisoformat(request.shift_start.replace('Z', '+00:00'))
        else:
            if 6 <= local_now.hour < 18:
                shift_start = local_now.replace(hour=6, minute=0, second=0, microsecond=0).replace(tzinfo=tz_info)
            else:
                if local_now.hour < 6:
                    yesterday = local_now - timedelta(days=1)
                    shift_start = yesterday.replace(hour=18, minute=0, second=0, microsecond=0).replace(tzinfo=tz_info)
                else:
                    shift_start = local_now.replace(hour=18, minute=0, second=0, microsecond=0).replace(tzinfo=tz_info)

        if request.shift_end:
            shift_end = datetime.fromisoformat(request.shift_end.replace('Z', '+00:00'))
        else:
            shift_end = now_aware

        shift_type = request.shift_type or ("DAY" if 6 <= shift_start.hour < 18 else "NIGHT")

        # Query work orders created or updated during this shift
        wo_response = supabase.table('work_orders').select('*').eq('user_id', current_user['user_id']).execute()
        all_wos = wo_response.data or []
        shift_wos = []
        for wo in all_wos:
            created_at = datetime.fromisoformat(wo.get('created_at').replace('Z', '+00:00')) if wo.get('created_at') else None
            updated_at = datetime.fromisoformat(wo.get('updated_at').replace('Z', '+00:00')) if wo.get('updated_at') else None
            
            is_in_shift = False
            if created_at and shift_start <= created_at <= shift_end:
                is_in_shift = True
            if updated_at and shift_start <= updated_at <= shift_end:
                is_in_shift = True
                
            if is_in_shift:
                shift_wos.append(wo)

        # Query query history entries during this shift
        query_response = supabase.table('query_history').select('*').eq('user_id', current_user['user_id']).execute()
        all_queries = query_response.data or []
        shift_queries = []
        for q in all_queries:
            created_at = datetime.fromisoformat(q.get('created_at').replace('Z', '+00:00')) if q.get('created_at') else None
            if created_at and shift_start <= created_at <= shift_end:
                shift_queries.append(q)

        # Query assets
        assets_response = supabase.table('user_assets').select('*').eq('user_id', current_user['user_id']).execute()
        assets = assets_response.data or []

        # Maintenance Status
        overdue_items = []
        due_this_week = []
        completed_maint_count = 0
        one_week_later = now_aware + timedelta(days=7)

        for asset in assets:
            if asset.get('next_maint'):
                try:
                    next_maint = datetime.fromisoformat(asset['next_maint'].replace('Z', '+00:00'))
                    if next_maint < now_aware:
                        overdue_items.append({
                            "asset_name": asset.get('name', 'Unknown'),
                            "task": "Preventative Maintenance",
                            "days_overdue": max((now_aware - next_maint).days, 1)
                        })
                    elif now_aware <= next_maint <= one_week_later:
                        due_this_week.append({
                            "asset_name": asset.get('name', 'Unknown'),
                            "task": "Preventative Maintenance",
                            "due_date": next_maint.isoformat()
                        })
                except Exception as e:
                    print(f"Error parsing next_maint: {e}")

        # Incidents (shift events where event_type = INCIDENT)
        events_response = supabase.table('shift_events').select('*').eq('user_id', current_user['user_id']).execute()
        all_events = events_response.data or []
        shift_incidents = []
        for e in all_events:
            created_at = datetime.fromisoformat(e.get('created_at').replace('Z', '+00:00')) if e.get('created_at') else None
            if created_at and shift_start <= created_at <= shift_end:
                if e.get('event_type') == 'INCIDENT':
                    shift_incidents.append({
                        "severity": e.get('severity', 'WARNING'),
                        "description": e.get('description', 'Unknown incident'),
                        "asset": e.get('asset_name', 'Unknown'),
                        "status": "OPEN",
                        "logged_by": "Operator"
                    })

        # Completed maintenance count (completed work orders during this shift)
        for wo in shift_wos:
            if wo.get('status') == 'COMPLETE':
                comp_at = datetime.fromisoformat(wo['completed_at'].replace('Z', '+00:00')) if wo.get('completed_at') else None
                if comp_at and shift_start <= comp_at <= shift_end:
                    completed_maint_count += 1

        # Assets Accessed Status
        accessed_assets = []
        for asset in assets:
            asset_queries = 0
            asset_wos = 0
            has_open_wo = False
            last_activity = None
            
            for q in shift_queries:
                if asset.get('name', '').lower() in q.get('query', '').lower():
                    asset_queries += 1
                    q_time = datetime.fromisoformat(q.get('created_at').replace('Z', '+00:00')) if q.get('created_at') else None
                    if q_time and (not last_activity or q_time > last_activity):
                        last_activity = q_time
            
            for wo in shift_wos:
                if wo.get('asset_id') == asset.get('id') or (wo.get('asset_name') and wo.get('asset_name') == asset.get('name')):
                    asset_wos += 1
                    if wo.get('status') in ['OPEN', 'IN_PROGRESS']:
                        has_open_wo = True
                    wo_time = datetime.fromisoformat(wo.get('updated_at', wo.get('created_at', '')).replace('Z', '+00:00')) if wo.get('updated_at') or wo.get('created_at') else None
                    if wo_time and (not last_activity or wo_time > last_activity):
                        last_activity = wo_time
            
            if asset_queries > 0 or asset_wos > 0:
                accessed_assets.append({
                    "name": asset.get('name'),
                    "queries_asked": asset_queries,
                    "work_orders": asset_wos,
                    "has_open_wo": has_open_wo,
                    "last_activity": last_activity.isoformat() if last_activity else shift_start.isoformat()
                })

        # Section 1 - Critical Items
        critical_items = []
        for wo in shift_wos:
            if wo.get('priority') == 'CRITICAL' and wo.get('status') != 'COMPLETE':
                critical_items.append({
                    "severity": "CRITICAL",
                    "type": "Work Order",
                    "description": f"Critical work order: {wo.get('title')}",
                    "asset": wo.get('asset_name', 'Unknown'),
                    "recommended_action": f"Verify status of {wo.get('title')} ({wo.get('id')}) immediately."
                })
        for item in overdue_items:
            critical_items.append({
                "severity": "CRITICAL",
                "type": "Maintenance",
                "description": f"Maintenance is overdue: {item['task']}",
                "asset": item["asset_name"],
                "recommended_action": f"Trigger maintenance workflow. Overdue by {item['days_overdue']} days."
            })
        for inc in shift_incidents:
            if inc["severity"] in ["HIGH", "CRITICAL"]:
                critical_items.append({
                    "severity": "CRITICAL",
                    "type": "Incident",
                    "description": f"Incident logged: {inc['description']}",
                    "asset": inc["asset"],
                    "recommended_action": "Conduct immediate physical safety verification."
                })
        for q in shift_queries:
            is_safety = any(kw in q.get('query', '').lower() for kw in ["safety", "hazard", "loto", "lockout", "emergency", "voltage", "pressure", "rpm", "torque"])
            is_low_conf = q.get('answer') and "does not contain" in q.get('answer').lower()
            if is_safety and is_low_conf:
                critical_items.append({
                    "severity": "CRITICAL",
                    "type": "Documentation Gap",
                    "description": f"Safety query returned low confidence: '{q.get('query')}'",
                    "asset": "General Plant",
                    "recommended_action": "Review procedures manually with supervisor."
                })

        # Activity Data Package for LLM
        activity_data = {
            "shift_type": shift_type,
            "facility_name": facility_name,
            "shift_wos": [{"id": wo.get('id'), "title": wo.get('title'), "priority": wo.get('priority'), "status": wo.get('status'), "asset": wo.get('asset_name')} for wo in shift_wos],
            "shift_queries": [{"query": q.get('query'), "confidence": "LOW" if (q.get('answer') and "does not contain" in q.get('answer').lower()) else "HIGH"} for q in shift_queries],
            "overdue_maintenance": overdue_items,
            "incidents": shift_incidents
        }

        # Call AI Report Generation
        ai_brief = await generate_ai_report(activity_data)

        # Store in shift_handovers table
        share_token = str(uuid.uuid4())
        handover_data = {
            "user_id": current_user['user_id'],
            "facility_name": facility_name,
            "shift_type": shift_type,
            "shift_start": shift_start.isoformat(),
            "shift_end": shift_end.isoformat(),
            "generated_at": now_aware.isoformat(),
            "generated_by_name": generated_by_name,
            "overall_status": ai_brief.get("overall_status", "AMBER"),
            "summary": ai_brief.get("summary", ""),
            "critical_items": critical_items,
            "work_orders_summary": shift_wos,
            "assets_accessed": accessed_assets,
            "maintenance_status": {
                "overdue_count": len(overdue_items),
                "due_this_week_count": len(due_this_week),
                "completed_count": completed_maint_count,
                "overdue_list": overdue_items
            },
            "queries_summary": shift_queries,
            "incidents_summary": shift_incidents,
            "ai_recommendations": ai_brief.get("ai_recommendations", []),
            "acknowledged_by": None,
            "acknowledged_at": None,
            "share_token": share_token,
            "created_at": now_aware.isoformat()
        }

        insert_response = supabase.table('shift_handovers').insert(handover_data).execute()
        if not insert_response.data:
            raise Exception("Failed to insert handover report")

        inserted_record = insert_response.data[0]

        # Recalculate facility health score
        try:
            from .facility import recalculate_health_score
            await recalculate_health_score(current_user['user_id'])
        except Exception as e:
            print(f"Health score recalculation failed: {e}")

        return inserted_record

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Handover generation failed: {str(e)}")

async def generate_ai_report(activity_data: Dict) -> Dict[str, Any]:
    """Call Groq or Gemini to generate brief summary and priorities."""
    system_prompt = (
        "You are an industrial operations AI.\n"
        "Based on the following shift activity data generate exactly 3 specific recommended "
        "priorities for the incoming shift lead. Reference asset names and work order IDs directly. "
        "Flag any safety-critical items first. Be direct and operational. No filler language."
    )
    
    user_prompt = f"""
    Shift Activity Data:
    - Shift Type: {activity_data['shift_type']}
    - Work Orders: {json.dumps(activity_data['shift_wos'])}
    - Gaps/Queries: {json.dumps(activity_data['shift_queries'])}
    - Overdue Maintenance: {json.dumps(activity_data['overdue_maintenance'])}
    - Incidents: {json.dumps(activity_data['incidents'])}

    Return ONLY a JSON response matching this structure:
    {{
      "overall_status": "GREEN|AMBER|RED",
      "summary": "One sentence AI summary of the shift.",
      "ai_recommendations": [
        "1. recommendation...",
        "2. recommendation...",
        "3. recommendation..."
      ]
    }}
    """

    # 1. Try Groq
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("your-"):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=15
            )
            if response.status_code == 200:
                res_data = response.json()
                return json.loads(res_data['choices'][0]['message']['content'])
        except Exception as e:
            print(f"[ERROR] Groq handover AI call failed: {e}")

    # 2. Try Gemini
    if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            response = model.generate_content(
                f"{system_prompt}\n\n{user_prompt}",
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"[ERROR] Gemini handover AI call failed: {e}")

    # 3. Fallback
    summary_sentence = "Shift completed with standard procedures."
    status = "GREEN"
    if activity_data['incidents'] or activity_data['overdue_maintenance']:
        status = "RED"
        summary_sentence = f"Shift completed with {len(activity_data['incidents'])} logged incidents and {len(activity_data['overdue_maintenance'])} overdue maintenance items."
    elif len(activity_data['shift_wos']) > 0:
        status = "AMBER"
        summary_sentence = f"Shift completed with active work orders on floor."

    recs = [
        "1. Complete safety walkthrough for incoming crew.",
        "2. Review all active and pending work orders in system.",
        "3. Ensure all safety-critical parameters are validated."
    ]
    if activity_data['overdue_maintenance']:
        recs[0] = f"1. Prioritize overdue maintenance tasks: {', '.join([item['asset_name'] for item in activity_data['overdue_maintenance'][:2]])}"
    if activity_data['shift_wos']:
        recs[1] = f"2. Continue work on Work Order {activity_data['shift_wos'][0].get('id', '')} for {activity_data['shift_wos'][0].get('asset', 'critical asset')}."

    return {
        "overall_status": status,
        "summary": summary_sentence,
        "ai_recommendations": recs
    }

@router.get("/api/handover/history")
async def get_handover_history(current_user: dict = Depends(get_current_user)):
    """Get last 20 handover reports for this user."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        response = supabase.table('shift_handovers')\
            .select('*')\
            .eq('user_id', current_user['user_id'])\
            .order('created_at', desc=True)\
            .limit(20)\
            .execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch handover history: {str(e)}")

@router.post("/api/handover/{handover_id}/acknowledge")
async def acknowledge_handover(
    handover_id: str,
    request: HandoverAcknowledgeRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Acknowledge handover brief."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        update_data = {
            "acknowledged_by": request.name,
            "acknowledged_at": now_iso
        }
        
        response = supabase.table('shift_handovers').update(update_data).eq('id', handover_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Handover report not found")
            
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge handover: {str(e)}")

@router.get("/api/handover/share/{share_token}")
async def get_shared_handover(share_token: str):
    """Retrieve read-only handover data publicly without auth."""
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        response = supabase.table('shift_handovers').select('*').eq('share_token', share_token).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Handover report not found")
        
        record = response.data[0]
        # Never return sensitive user account information
        record.pop('user_id', None)
        return record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch shared brief: {str(e)}")
