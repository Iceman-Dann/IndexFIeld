import os

routes_dir = "backend/routes"
routers = [f for f in os.listdir(routes_dir) if f.endswith(".py") and f != "__init__.py"]

template_imports = """from fastapi import APIRouter, Request
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
"""

for router_file in routers:
    name = router_file.replace(".py", "")
    content = f"""{template_imports}
@router.get("/{name}")
async def serve_{name}_page(request: Request):
    \"\"\"Serve the {name} page using Jinja2 templates.\"\"\"
    return templates.TemplateResponse("{name}-view.html", {{"request": request}})
"""
    with open(os.path.join(routes_dir, router_file), "w", encoding="utf-8") as f:
        f.write(content)

print(f"Successfully updated {len(routers)} routers to use Jinja2Templates.")
