from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from datetime import datetime
import json
import time

from .document_processor import DocumentProcessor
from .vector_store import VectorStore
from .rag_engine import RAGEngine
from .document_skeleton import SkeletonExtractor
from .config import get_settings
from .middleware import get_user_context, check_sandbox_limits, format_error_response

# Import route modules
from .routes import auth, facility, chat, manuals, assets, workorders

app = FastAPI(title="IndexField API", version="2.0.0")

settings = get_settings()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests for monitoring."""
    start_time = time.time()
    
    # Extract user info if available
    user_id = None
    facility_id = None
    
    # TODO: Extract from JWT token if present
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    
    # TODO: Log to query_history table
    
    return response

# Static files - serve from parent directory
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=PARENT_DIR), name="static")

# Ensure directories exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize components
doc_processor = DocumentProcessor()
vector_store = VectorStore()
skeleton_extractor = SkeletonExtractor()
rag_engine = RAGEngine(skeleton_extractor)

# Include route modules
app.include_router(auth.router)
app.include_router(facility.router)
app.include_router(chat.router)
app.include_router(manuals.router)
app.include_router(assets.router)
app.include_router(workorders.router)

# --- Models ---
class QueryRequest(BaseModel):
    query: str
    manual_id: Optional[str] = None
    top_k: int = 3
    context: Optional[str] = None

class ChunkResult(BaseModel):
    text: str
    page_number: int
    chunk_index: int
    manual_id: str
    manual_name: str
    score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[ChunkResult]
    citations: List[str]

# --- Health Check ---
@app.get("/")
async def root():
    return FileResponse(os.path.join(PARENT_DIR, "index.html"))


@app.get("/favicon.png")
async def serve_favicon():
    path = os.path.join(PARENT_DIR, "favicon.png")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})

@app.get("/signin.html")
async def serve_signin():
    return FileResponse(os.path.join(PARENT_DIR, "signin.html"))

@app.get("/setup-wizard.html")
async def serve_setup_wizard():
    return FileResponse(os.path.join(PARENT_DIR, "setup-wizard.html"))

@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse(os.path.join(PARENT_DIR, "dashboard.html"))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# --- API Status ---
@app.get("/api")
async def api_status():
    return {"status": "IndexField API Operational", "version": "2.0.0"}

# --- Legacy Endpoints (will be migrated to route modules) ---
@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest, context: dict = Depends(get_user_context)):
    """Query the RAG system for answers with citations."""
    try:
        # Check sandbox limits
        if not await check_sandbox_limits(context, "query"):
            raise HTTPException(
                status_code=402,
                detail="Query limit reached for sandbox account"
            )
        
        # If user provided pasted context, use it directly with the LLM
        if request.context and len(request.context.strip()) > 50:
            answer, sources = rag_engine.query_with_context(
                request.query, 
                context=request.context
            )
        else:
            answer, sources = rag_engine.query(
                request.query, 
                manual_id=request.manual_id,
                top_k=request.top_k
            )
        
        # Format citations
        citations = [
            f"Source: {s.manual_name} - Page {s.page_number}"
            for s in sources
        ]
        
        # Update query count if sandbox
        facility = context.get("facility")
        if facility and facility.get("account_type") == "sandbox":
            # TODO: Update query count in database
            pass
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            citations=citations
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("QUERY_FAILED", "Query processing failed", str(e))
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
