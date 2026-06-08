from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize templates. We add both the project root (to find templates/base.html) 
# and dashboard-pages (to find the specific fragments).
templates = Jinja2Templates(directory=[
    os.path.join(PROJECT_ROOT, "templates"),
    os.path.join(PROJECT_ROOT, "dashboard-pages")
])

@router.get("/telemetry")
async def serve_telemetry_page(request: Request):
    """Serve the telemetry page using Jinja2 templates."""
    return templates.TemplateResponse("telemetry-view.html", {"request": request})
