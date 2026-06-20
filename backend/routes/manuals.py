"""Manuals and document management routes."""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from ..middleware import get_user_context, check_sandbox_limits, format_error_response
from ..config import get_settings
from supabase import create_client
import os, json

router = APIRouter(prefix="/api/manuals", tags=["manuals"])
settings = get_settings()
supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
supabase = create_client(settings.SUPABASE_URL, supabase_key)

# In-memory fallback for demo/manual uploads when Supabase is not available
local_manuals: List[Dict[str, Any]] = []

# Persistent fallback storage path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOCAL_MANUALS_PATH = os.path.join(PROJECT_ROOT, "uploads", "local_manuals.json")


def _load_local_manuals():
    global local_manuals
    try:
        if os.path.exists(LOCAL_MANUALS_PATH):
            with open(LOCAL_MANUALS_PATH, "r", encoding="utf-8") as f:
                local_manuals = json.load(f)
        else:
            local_manuals = []
    except Exception:
        local_manuals = []


def _save_local_manuals():
    try:
        os.makedirs(os.path.dirname(LOCAL_MANUALS_PATH), exist_ok=True)
        with open(LOCAL_MANUALS_PATH, "w", encoding="utf-8") as f:
            json.dump(local_manuals, f)
    except Exception:
        pass


# Load existing fallback manuals on import
_load_local_manuals()


class ManualResponse(BaseModel):
    """Response model for manual data."""
    id: str
    filename: str
    asset_type: str
    status: str
    page_count: int
    chunk_count: int
    created_at: str


@router.get("/", response_model=List[ManualResponse])
async def list_manuals(context: dict = Depends(get_user_context)):
    """List all manuals for the user's facility."""
    facility_id = context.get("facility_id")

    # If no facility (demo/guest), return local persisted manuals
    if not facility_id:
        return local_manuals

    # Attempt to fetch from Supabase, but always include any locally-stored manuals
    manuals: List[ManualResponse] = []
    try:
        response = supabase.table("documents").select("*").eq("facility_id", facility_id).execute()
        for doc in (response.data or []):
            manuals.append(
                ManualResponse(
                    id=doc["id"],
                    filename=doc.get("filename", ""),
                    asset_type=doc.get("asset_type", "Industrial Equipment"),
                    status=doc.get("status", ""),
                    page_count=doc.get("page_count", 0),
                    chunk_count=doc.get("chunk_count", 0),
                    created_at=doc.get("created_at", "")
                )
            )
    except Exception:
        # If supabase fails, continue and return local manuals only
        manuals = []

    # Also include any locally persisted manuals so demo uploads are visible
    for entry in local_manuals:
        manuals.append(
            ManualResponse(
                id=entry["id"],
                filename=entry.get("filename", ""),
                asset_type=entry.get("asset_type", "Industrial Equipment"),
                status=entry.get("status", ""),
                page_count=entry.get("page_count", 0),
                chunk_count=entry.get("chunk_count", 0),
                created_at=entry.get("created_at", "")
            )
        )

    
    return manuals


@router.post("/upload")
async def upload_manual(
    file: UploadFile = File(...),
    asset_type: str = Query(default="Industrial Equipment"),
    context: dict = Depends(get_user_context)
):
    """
    Upload and process a manual.
    Checks sandbox limits before processing.
    """
    facility_id = context.get("facility_id")
    user_id = context["user_id"]
    
    # Allow demo uploads for guest users by using a demo facility id
    if not facility_id:
        facility_id = "demo_facility"
    
    try:
        # Check sandbox limits
        if not await check_sandbox_limits(context, "document_upload"):
            raise HTTPException(
                status_code=402,
                detail=format_error_response("DOCUMENT_LIMIT_REACHED", "Document upload limit reached for sandbox account")
            )
        
        # TODO: Implement actual file processing with RAG pipeline
        # For now, create a placeholder record
        
        manual_id = str(uuid.uuid4())
        
        manual_record = {
            "id": manual_id,
            "facility_id": facility_id,
            "user_id": user_id,
            "filename": file.filename,
            "asset_type": asset_type,
            "status": "processing",
            "page_count": 0,
            "chunk_count": 0,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            response = supabase.table("documents").insert(manual_record).execute()
            if response.data:
                return {
                    "success": True,
                    "manual_id": manual_id,
                    "message": "Manual upload started. Processing in background."
                }
        except Exception:
            # Fall back to local in-memory store for demo environments
            entry = {
                "id": manual_id,
                "facility_id": facility_id,
                "filename": file.filename,
                "asset_type": asset_type,
                "status": "Ready",
                "page_count": 0,
                "chunk_count": 0,
                "created_at": datetime.now().isoformat()
            }
            local_manuals.append(entry)
            _save_local_manuals()
            return {
                "success": True,
                "manual_id": manual_id,
                "message": "Manual stored locally for demo (supabase unavailable)."
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("MANUAL_UPLOAD_FAILED", "Failed to upload manual", str(e))
        )


@router.get("/debug_local")
async def debug_local_manuals():
    """Debug endpoint: return the in-memory local_manuals (for dev)."""
    return local_manuals


@router.delete("/{manual_id}")
async def delete_manual(
    manual_id: str,
    context: dict = Depends(get_user_context)
):
    """Delete a manual."""
    facility_id = context.get("facility_id")
    
    if not facility_id:
        raise HTTPException(
            status_code=400,
            detail="No facility associated with user"
        )
    
    try:
        # Check if manual belongs to user's facility
        response = supabase.table("documents").select("*").eq("id", manual_id).eq("facility_id", facility_id).single()
        
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Manual not found or access denied"
            )
        
        # Delete manual
        supabase.table("documents").delete().eq("id", manual_id).execute()
        
        return {"success": True, "message": "Manual deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("MANUAL_DELETE_FAILED", "Failed to delete manual", str(e))
        )
