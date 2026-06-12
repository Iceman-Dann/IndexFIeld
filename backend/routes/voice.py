from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import os
import requests
from config import settings

router = APIRouter()
security = HTTPBearer()

class TranscribeResponse(BaseModel):
    success: bool
    text: str
    error: Optional[str] = None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info from Supabase."""
    from supabase import create_client
    from jose import jwt, JWTError
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # Verify with Supabase
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        user_response = supabase.auth.get_user(token)
        
        return {
            "user_id": user_id,
            "token": token,
            "email": user_response.user.email if user_response.user else None
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@router.post("/api/voice/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Transcribe audio file using Groq Whisper API.
    Counts as one query against query_count.
    """
    # Check paywall limits for sandbox users
    from supabase import create_client
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    try:
        # Get user profile to check account type and query count
        profile_response = supabase.table('profiles').select('account_type, query_count').eq('id', current_user['user_id']).execute()
        
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        profile = profile_response.data[0]
        account_type = profile.get('account_type', 'sandbox')
        query_count = profile.get('query_count', 0)
        
        # Sandbox limit check
        if account_type == 'sandbox' and query_count >= 2:
            raise HTTPException(status_code=402, detail="Query limit reached for sandbox account")
        
        # Read audio file
        audio_data = await file.read()
        
        # Check if Groq API key is available
        if not settings.GROQ_API_KEY:
            # Fallback: return mock transcription for demo
            return TranscribeResponse(
                success=True,
                text="[DEMO MODE] Audio transcription requires Groq API key. Configure GROQ_API_KEY in .env file."
            )
        
        # Call Groq Whisper API
        groq_api_url = "https://api.groq.com/openai/v1/audio/transcriptions"
        
        files = {
            'file': (file.filename, audio_data, file.content_type or 'audio/wav')
        }
        data = {
            'model': 'whisper-large-v3',
            'response_format': 'text'
        }
        headers = {
            'Authorization': f'Bearer {settings.GROQ_API_KEY}'
        }
        
        response = requests.post(groq_api_url, files=files, data=data, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Groq API error: {response.text}"
            )
        
        transcribed_text = response.text.strip()
        
        # Increment query count
        supabase.table('profiles').update({'query_count': query_count + 1}).eq('id', current_user['user_id']).execute()
        
        return TranscribeResponse(
            success=True,
            text=transcribed_text
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
