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

@router.get("/manuals")
async def serve_manuals_page(request: Request):
    """Serve the manuals page using Jinja2 templates."""
    return templates.TemplateResponse("manuals-view.html", {"request": request})
