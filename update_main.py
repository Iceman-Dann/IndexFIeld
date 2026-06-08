import re

def update_main():
    with open("backend/main_enhanced.py", "r") as f:
        content = f.read()

    routers = ["chat", "insights", "assets", "telemetry", "vault", "field", "loto", "prognostics", "history", "help", "manuals"]
    
    # 1. Add imports
    imports = "\n".join([f"from backend.routes.{r} import router as {r}_router" for r in routers])
    inclusions = "\n".join([f"app.include_router({r}_router)" for r in routers])
    
    # Insert after app definition
    pattern = r'(app = FastAPI\([\s\S]*?\n\))'
    replacement = f"\\1\n\n# Include MPA Routers\n{imports}\n\n{inclusions}\n"
    
    if "from backend.routes.chat import router" not in content:
        content = re.sub(pattern, replacement, content)
        
    with open("backend/main_enhanced.py", "w") as f:
        f.write(content)
        
    print("Successfully updated main_enhanced.py with router inclusions.")

if __name__ == "__main__":
    update_main()
