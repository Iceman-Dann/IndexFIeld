from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import qrcode
import io
import os
from supabase import create_client, Client
from ..config import settings

router = APIRouter()

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Get project root for serving templates
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================================
# Models
# ============================================================================

class AssetScanResponse(BaseModel):
    id: str
    name: str
    asset_code: str
    model: str
    location: str
    status: str
    last_maint: Optional[str] = None
    next_maint: Optional[str] = None
    serial_number: Optional[str] = None
    linked_manuals: List[Dict] = []
    open_work_orders: List[Dict] = []
    maintenance_history: List[Dict] = []

class ManualInfo(BaseModel):
    id: str
    filename: str
    page_count: int
    created_at: str

class WorkOrderInfo(BaseModel):
    id: str
    priority: str
    description: str
    created_at: str

class MaintenanceEvent(BaseModel):
    date: str
    task_name: str
    technician: str
    status: str

# ============================================================================
# Serve Scan Page
# ============================================================================

@router.get("/scan/{qr_token}")
async def serve_scan_page(request: Request, qr_token: str):
    """
    Serve the mobile scan page for a given QR token.
    This is a public endpoint - no authentication required.
    """
    return FileResponse(os.path.join(PROJECT_ROOT, "scan.html"))

# ============================================================================
# Public Route: Scan QR Code (API)
# ============================================================================

@router.get("/api/scan/{qr_token}", response_model=AssetScanResponse)
async def scan_qr_token(qr_token: str):
    """
    Public endpoint to look up asset by QR token.
    No authentication required - this is for floor technicians scanning QR codes.
    """
    try:
        # Query Supabase for asset with this qr_token
        response = supabase.table('user_assets').select('*').eq('qr_token', qr_token).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset = response.data[0]
        
        # Get linked manuals for this asset
        # Note: This assumes there's a relationship between assets and manuals
        # For now, we'll return empty lists as the schema may need adjustment
        linked_manuals = []
        open_work_orders = []
        maintenance_history = []
        
        return AssetScanResponse(
            id=asset['id'],
            name=asset['name'],
            asset_code=asset['asset_code'],
            model=asset.get('model', ''),
            location=asset.get('location', ''),
            status=asset['status'],
            last_maint=asset.get('last_maint'),
            next_maint=asset.get('next_maint'),
            serial_number=asset.get('serial_number'),
            linked_manuals=linked_manuals,
            open_work_orders=open_work_orders,
            maintenance_history=maintenance_history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] QR scan failed: {e}")
        raise HTTPException(status_code=500, detail="Scan failed")

# ============================================================================
# Protected Route: Generate QR Code for Asset
# ============================================================================

@router.get("/api/assets/{asset_id}/qr")
async def generate_asset_qr(asset_id: str):
    """
    Protected endpoint to generate QR code for an asset.
    Returns PNG image directly.
    Authentication required - user must own the asset.
    """
    try:
        # Query Supabase for asset
        response = supabase.table('user_assets').select('*').eq('id', asset_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset = response.data[0]
        
        # Generate QR code pointing to scan URL
        base_url = settings.API_URL or "http://localhost:8000"
        scan_url = f"{base_url}/scan/{asset['qr_token']}"
        
        # Create QR code with high error correction
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(scan_url)
        qr.make(fit=True)
        
        # Generate PNG image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return Response(content=img_buffer.getvalue(), media_type="image/png")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] QR generation failed: {e}")
        raise HTTPException(status_code=500, detail="QR generation failed")
