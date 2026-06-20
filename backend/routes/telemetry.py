from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
import os

router = APIRouter()
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@router.get("/telemetry/view")
async def serve_telemetry_page(request: Request):
    """Serve the static telemetry dashboard fragment to be loaded into the SPA."""
    file_path = os.path.join(PROJECT_ROOT, "dashboard-pages", "telemetry-view.html")
    return FileResponse(file_path)
