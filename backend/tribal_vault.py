from supabase import create_client
from config import settings
import uuid
import datetime

# Initialize Supabase client
# Fallback to a mock if keys are missing to prevent crashes during demo
supabase = None
if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    except Exception as e:
        print(f"[WARN] Supabase client initialization failed: {e}")

# In-memory storage for air-gapped demo mode if Supabase is offline
demo_notes = []

def record_tribal_note(session_id, page, author, img_url, ocr):
    """Store a newly extracted tribal note."""
    data = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "page": page,
        "author": author,
        "raw_image_url": img_url,
        "ocr_text": ocr,
        "type": "pending",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }
    
    if supabase:
        try:
            supabase.table("tribal_notes").insert(data).execute()
        except Exception as e:
            print(f"[ERROR] Failed to insert tribal note to Supabase: {e}")
            demo_notes.append(data)
    else:
        demo_notes.append(data)
        
    return data["id"]

def get_tribal_notes(status="pending"):
    """Fetch tribal notes by status."""
    if supabase:
        try:
            resp = supabase.table("tribal_notes").select("*").eq("type", status).order("created_at", desc=True).execute()
            return resp.data
        except Exception as e:
            print(f"[ERROR] Failed to fetch tribal notes: {e}")
            return [n for n in demo_notes if n["type"] == status]
    return [n for n in demo_notes if n["type"] == status]

def update_note_status(note_id, new_type, edited_text=None):
    """Update note status and log to audit trail."""
    updates = {
        "type": new_type,
        "updated_at": datetime.datetime.utcnow().isoformat()
    }
    if edited_text is not None:
        updates["ocr_text"] = edited_text
        
    if supabase:
        try:
            supabase.table("tribal_notes").update(updates).eq("id", note_id).execute()
            # Log audit
            audit_entry = {
                "id": str(uuid.uuid4()),
                "note_id": note_id,
                "action": new_type,
                "actor_id": "admin",
                "comment": edited_text or "",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            supabase.table("tribal_audit").insert(audit_entry).execute()
        except Exception as e:
            print(f"[ERROR] Failed to update tribal note: {e}")
            # Update local fallback
            for n in demo_notes:
                if n["id"] == note_id:
                    n.update(updates)
                    break
    else:
        for n in demo_notes:
            if n["id"] == note_id:
                n.update(updates)
                break
    return True

def check_unsafe_notes(session_id, pages):
    """Check if any of the retrieved pages have been flagged as 'unsafe'."""
    if supabase:
        try:
            resp = supabase.table("tribal_notes").select("page, ocr_text").eq("session_id", session_id).eq("type", "unsafe").in_("page", pages).execute()
            return resp.data
        except Exception as e:
            print(f"[ERROR] Failed to check safety flags: {e}")
            return []
    return [n for n in demo_notes if n["session_id"] == session_id and n["type"] == "unsafe" and n["page"] in pages]
