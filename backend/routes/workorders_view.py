from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from typing import Optional

router = APIRouter()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info from Supabase."""
    from jose import jwt, JWTError
    from config import settings
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        return {"user_id": user_id, "token": token}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

@router.get("/workorders", response_class=HTMLResponse)
async def serve_workorders_view(current_user: dict = Depends(get_current_user)):
    """Serve the work orders dashboard view."""
    import os
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(PROJECT_ROOT, "dashboard-pages", "work-orders-view.html"))
