from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from typing import Optional
import os

router = APIRouter()
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    from jose import jwt, JWTError
    import uuid
    from ..config import settings

    if not credentials:
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        return {"user_id": guest_id, "is_guest": True}
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise Exception("No sub")
        return {"user_id": user_id, "token": token}
    except Exception:
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        return {"user_id": guest_id, "is_guest": True}


@router.get("/team")
async def serve_team_view(current_user: dict = Depends(get_current_user)):
    """Serve the Team Management dashboard view."""
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return FileResponse(os.path.join(PROJECT_ROOT, "dashboard-pages", "team-view.html"))
