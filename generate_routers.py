import os

routers = [
    ("chat", "chat-view.html", "Chat interface and document querying logic"),
    ("insights", "insights-view.html", "Performance and operational insights logic"),
    ("assets", "assets-view.html", "Equipment and asset management logic"),
    ("telemetry", "telemetry-view.html", "Live monitoring and sensor data logic"),
    ("vault", "vault-view.html", "Knowledge verification and tribal notes logic"),
    ("field", "field-view.html", "Field technician operations logic"),
    ("loto", "loto-view.html", "Lockout/Tagout safety logic"),
    ("prognostics", "prognostics-view.html", "Maintenance forecasting and ROI logic"),
    ("history", "history-view.html", "Search history and analytics logic"),
    ("help", "help-view.html", "Help center and onboarding logic"),
    ("manuals", "manuals-view.html", "Manual registry and uploading logic")
]

routes_dir = "backend/routes"
os.makedirs(routes_dir, exist_ok=True)

# Generate __init__.py
with open(os.path.join(routes_dir, "__init__.py"), "w") as f:
    f.write("# Modular routers for IndexField MPA\n")

# Generate each router
for name, html_file, desc in routers:
    content = f'''from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter(tags=["{name}"])
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@router.get("/{name}")
async def serve_{name}_page():
    """Serve the standalone {name} page."""
    file_path = os.path.join(PROJECT_ROOT, "dashboard-pages", "{html_file}")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {{"error": "Page not found"}}

# Add {desc} below
'''
    with open(os.path.join(routes_dir, f"{name}.py"), "w") as f:
        f.write(content)

print(f"Successfully generated {len(routers)} routers in {routes_dir}")
