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

@router.get("/insights")
async def serve_insights_page(request: Request):
    """Serve the insights page using Jinja2 templates."""
    return templates.TemplateResponse("insights-view.html", {"request": request})

@router.get("/api/insights")
async def get_insights():
    """Get operational intelligence data."""
    # This matches the endpoint called by the frontend.
    from backend.main_enhanced import get_insights
    return await get_insights()
