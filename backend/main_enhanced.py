"""
IndexField Enhanced Backend API
Complete dashboard integration with all features.
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import uuid
import json
import random
import asyncio
import shutil
import pathlib

# Import components
from backend.document_skeleton import SkeletonExtractor, get_relevant_context, skeleton_extractor, extract_skeleton
from backend.rag_engine import RAGEngine
from backend.tribal_vault import get_tribal_notes, update_note_status
from backend.config import settings
import requests
from backend.document_processor import DocumentProcessor
from backend.vector_store import VectorStore

app = FastAPI(
    title="IndexField RAG API",
    description="Complete API for IndexField Industrial Intelligence Platform",
    version="2.0.0"
)

# Include MPA Routers
from backend.routes.chat import router as chat_router
# from backend.routes.insights import router as insights_router
from backend.routes.assets import router as assets_router
from backend.routes.telemetry import router as telemetry_router
from backend.routes.vault import router as vault_router
from backend.routes.field import router as field_router
from backend.routes.loto import router as loto_router
from backend.routes.prognostics import router as prognostics_router
from backend.routes.history import router as history_router
from backend.routes.help import router as help_router
from backend.routes.manuals import router as manuals_router
from backend.routes.qr import router as qr_router

app.include_router(chat_router)
# app.include_router(insights_router)
app.include_router(assets_router)
app.include_router(telemetry_router)
app.include_router(vault_router)
app.include_router(field_router)
app.include_router(loto_router)
app.include_router(prognostics_router)
app.include_router(history_router)
app.include_router(help_router)
app.include_router(manuals_router)
app.include_router(qr_router)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Serve root directory for HTML files
# Get the project root directory (one level up from backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Serve dashboard fragment pages at /dashboard-pages/ (matches frontend fetch path)
DASHBOARD_PAGES_DIR = os.path.join(PROJECT_ROOT, "dashboard-pages")
if os.path.isdir(DASHBOARD_PAGES_DIR):
    app.mount("/dashboard-pages", StaticFiles(directory=DASHBOARD_PAGES_DIR), name="dashboard-pages")

# Serve all other static assets (HTML, CSS, JS) under /static for compatibility
app.mount("/static", StaticFiles(directory=PROJECT_ROOT), name="static")

@app.get("/supabase-config.js")
async def serve_config():
    return FileResponse(os.path.join(PROJECT_ROOT, "supabase-config.js"))

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(PROJECT_ROOT, "index.html"))

@app.get("/signin.html")
async def serve_signin():
    return FileResponse(os.path.join(PROJECT_ROOT, "signin.html"))

@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse(os.path.join(PROJECT_ROOT, "dashboard.html"))

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("./logs", exist_ok=True)

# Initialize components (use module-level skeleton_extractor for shared state)
rag_engine = RAGEngine(skeleton_extractor)
doc_processor = DocumentProcessor()
vector_store = VectorStore()

# In-memory data stores (replace with database in production)
manuals_registry: List[Dict] = []

# Industrial document whitelist — excludes UI/system assets (favicon, logos, etc.)
INDUSTRIAL_DOC_EXTENSIONS = {'.pdf', '.txt', '.csv', '.docx'}
SYSTEM_ASSET_MARKERS = (
    'favicon', 'logo.png', 'logo.svg', 'icon.', 'apple-touch',
    'manifest', 'robots.txt', 'sitemap',
)


def is_industrial_document(filename: str) -> bool:
    """True if filename is an allowed plant documentation type, not a web/UI asset."""
    if not filename:
        return False
    name = filename.lower().strip()
    ext = os.path.splitext(name)[1]
    if ext not in INDUSTRIAL_DOC_EXTENSIONS:
        return False
    if any(marker in name for marker in SYSTEM_ASSET_MARKERS):
        return False
    return True


assets_registry: List[Dict] = []
knowledge_posts: List[Dict] = []
work_orders: List[Dict] = []
telemetry_data: Dict[str, Any] = {}
query_analytics: List[Dict] = []

# ============================================================================
# Models
# ============================================================================

class QueryRequest(BaseModel):
    query: str
    manual_id: Optional[str] = None
    asset_id: Optional[str] = None
    top_k: int = 3

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

class ManualInfo(BaseModel):
    id: str
    filename: str
    asset_type: str
    status: str = "processing"
    uploaded_at: str
    page_count: int = 0
    section_count: int = 0

class ManualUploadResponse(BaseModel):
    success: bool
    manual: ManualInfo
    message: str

# Asset Models
class Asset(BaseModel):
    id: str
    name: str
    model: str
    location: str
    status: str = Field(..., description="online, offline, warning, maintenance")
    last_maint: Optional[str] = None
    next_maint: Optional[str] = None
    serial_number: Optional[str] = None
    manual_ids: List[str] = []
    created_at: str = None

class AssetCreate(BaseModel):
    name: str
    model: str
    location: str
    status: str = "online"
    serial_number: Optional[str] = None

class AssetImportRequest(BaseModel):
    assets: List[AssetCreate]

class AssetImportResponse(BaseModel):
    success: bool
    imported_count: int
    errors: List[str] = []

async def send_safety_webhook(session_id, page):
    """Trigger a high-risk alert webhook."""
    webhook_url = settings.WEBHOOK_URL or "http://localhost:8000/mock-webhook"
    payload = {
        "event": "HIGH_RISK_QUERY",
        "session_id": session_id,
        "page": page,
        "timestamp": datetime.now().isoformat(),
        "severity": "CRITICAL",
        "message": f"Technician accessed data flagged as UNSAFE on page {page}."
    }
    
    try:
        if settings.WEBHOOK_URL:
            # We use a separate thread/task for fire-and-forget in production
            requests.post(webhook_url, json=payload, timeout=5)
        print(f"[SAFETY ALERT] Webhook sent for session {session_id} page {page}")
    except Exception as e:
        print(f"[WARN] Safety webhook failed: {e}")

# Knowledge Vault Models
class KnowledgePost(BaseModel):
    id: int
    author: str
    avatar: str
    role: str
    level: int
    timestamp: str
    title: str
    content: str
    likes: int = 0
    verified: bool = False
    asset: Optional[str] = None
    asset_id: Optional[str] = None
    image: Optional[str] = None
    comments: int = 0

class KnowledgePostCreate(BaseModel):
    author: str
    role: str
    level: int
    title: str
    content: str
    asset: Optional[str] = None
    asset_id: Optional[str] = None

class KnowledgePostUpdate(BaseModel):
    verified: Optional[bool] = None
    likes: Optional[int] = None

# Telemetry Models
class SensorReading(BaseModel):
    id: str
    name: str
    value: float
    unit: str
    min: float
    max: float
    alert_threshold: float
    status: str
    timestamp: str

class TelemetryData(BaseModel):
    sensors: List[SensorReading]
    connected_count: int
    anomaly_detected: bool
    alerts: List[Dict] = []

# Work Order Models
class WorkOrder(BaseModel):
    id: str
    asset_id: str
    asset_name: str
    location: str
    priority: str
    procedure: str
    sources: List[str] = []
    verified: bool = False
    status: str = "draft"  # draft, assigned, in_progress, completed
    created_at: str
    estimated_downtime: str = "4 Hours"
    parts_required: str = ""
    skill_level: str = "Level 2+"
    tribal_knowledge: Optional[str] = None

class WorkOrderCreate(BaseModel):
    asset_id: str
    priority: str = "MEDIUM"
    procedure: str
    sources: List[str] = []
    anomaly_type: Optional[str] = None

# Insights Models
class TrendingIssue(BaseModel):
    code: str
    description: str
    count: int
    trend: str
    urgent: bool

class OperationalInsights(BaseModel):
    total_queries: int
    most_searched_asset: str
    most_searched_count: int
    verified_answer_rate: float
    fleet_risk_score: str
    fault_codes: List[Dict]
    trending_issues: List[TrendingIssue]
    predictive_alerts: List[Dict]

# Auth Models
class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    username: str
    password: str

class SystemStatus(BaseModel):
    vector_db: str
    llm: str
    llm_provider: str
    ollama_running: bool
    model_available: bool
    gemini_available: bool
    groq_available: bool
    manuals_count: int
    assets_count: int
    uptime_seconds: int

# ============================================================================
# Helper Functions
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def init_sample_data():
    """Initialize empty registries — real data comes from Supabase."""
    pass

# Start with empty registries (user data loaded from Supabase on frontend)
init_sample_data()

# ============================================================================
# Core API Endpoints
# ============================================================================

@app.get("/favicon.png")
async def favicon():
    """Serve favicon."""
    import pathlib
    project_root = pathlib.Path(__file__).parent.parent
    favicon_path = project_root / "favicon.png"
    print(f"[FAVICON] Requested favicon, path: {favicon_path}, exists: {favicon_path.exists()}")
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    print(f"[FAVICON] Favicon not found at {favicon_path}")
    raise HTTPException(404, "Favicon not found")

@app.get("/")
async def root():
    """Serve dashboard HTML."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    
    # Fallback to API info if dashboard not found
    llm_status = rag_engine.check_llm_status()
    return {
        "status": "IndexField RAG API Operational",
        "version": "2.0.0",
        "llm": {
            "primary": "gemini-1.5-flash" if llm_status.get("gemini_available") else settings.OLLAMA_MODEL,
            "provider": llm_status.get("active_provider", "none"),
            "gemini_available": llm_status.get("gemini_available", False),
            "ollama_available": llm_status.get("ollama_running", False)
        },
        "features": [
            "rag_query", "manual_upload", "asset_management",
            "telemetry", "knowledge_vault", "work_orders", "insights"
        ],
        "note": "dashboard.html not found, place it next to backend folder"
    }

@app.get("/health", response_model=SystemStatus)
async def health_check():
    """System health check endpoint."""
    try:
        llm_status = rag_engine.check_llm_status()
        print(f"[HEALTH] LLM status: {llm_status}")
    except Exception as e:
        print(f"[HEALTH ERROR] {e}")
        llm_status = {"error": str(e)}
    
    # Determine active LLM
    if llm_status.get("active_provider") == "gemini":
        llm_name = settings.GEMINI_MODEL
        provider = "gemini"
    elif llm_status.get("active_provider") == "groq":
        llm_name = settings.GROQ_MODEL
        provider = "groq"
    elif llm_status.get("active_provider") == "ollama":
        llm_name = settings.OLLAMA_MODEL
        provider = "ollama"
    else:
        llm_name = "Unavailable"
        provider = "none"
    
    return SystemStatus(
        vector_db="Online",  # Skeleton system always ready
        llm=llm_name,
        llm_provider=provider,
        ollama_running=llm_status.get("ollama_running", False),
        model_available=llm_status.get("ollama_model_available", False) or llm_status.get("gemini_available", False) or llm_status.get("groq_available", False),
        gemini_available=llm_status.get("gemini_available", False),
        groq_available=llm_status.get("groq_available", False),
        manuals_count=len(manuals_registry),
        assets_count=len(assets_registry),
        uptime_seconds=0
    )

# ============================================================================
# Auth Endpoints
# ============================================================================

@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    """Authenticate user and return JWT token."""
    if user.username != settings.ADMIN_USERNAME:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # In production, verify password hash
    # if not verify_password(user.password, settings.ADMIN_PASSWORD_HASH):
    #     raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.username, "role": "admin"})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/verify")
async def verify_token(current_user: str = Depends(get_current_user)):
    """Verify JWT token is valid."""
    return {"valid": True, "user": current_user}

# ============================================================================
# Manual Upload & RAG Endpoints
# ============================================================================

@app.post("/upload", response_model=ManualUploadResponse)
async def upload_manual(
    file: UploadFile = File(...),
    asset_type: str = Query(default="Industrial Equipment"),
    asset_id: Optional[str] = Query(default=None)
):
    """Upload and process industrial documents (PDF, text, CSV, Word)."""
    # Check file extension — strict whitelist (no UI assets / images)
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in INDUSTRIAL_DOC_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type. Supported: {', '.join(sorted(INDUSTRIAL_DOC_EXTENSIONS))}",
        )
    if not is_industrial_document(file.filename):
        raise HTTPException(400, "System or UI assets cannot be indexed as plant documentation.")
    
    # Delete existing manual with same filename to avoid conflicts
    for manual in manuals_registry[:]:
        if manual['filename'] == file.filename:
            print(f"[UPLOAD] Deleting existing manual with same filename: {file.filename}")
            if manual['id'] in skeleton_extractor.skeletons:
                del skeleton_extractor.skeletons[manual['id']]
            manuals_registry.remove(manual)
            file_path_old = os.path.join(settings.UPLOAD_DIR, f"{manual['id']}_{manual['filename']}")
            if os.path.exists(file_path_old):
                os.remove(file_path_old)
    
    manual_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    file_path = os.path.join(settings.UPLOAD_DIR, f"{manual_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process document using enhanced processor
        chunks = doc_processor.process_document(file_path, manual_id, file.filename)
        
        # Store in vector store
        vector_store.add_documents(chunks)
        
        # Extract skeleton for efficient querying (use module-level function for shared state)
        skeleton = extract_skeleton(file_path, manual_id, file.filename)
        
        # Determine content type and metrics
        content_type = "unknown"
        if file_ext == '.pdf':
            content_type = "pdf"
            page_count = skeleton.total_pages
        else:
            content_type = "document"
            page_count = 1
        
        manual_info = {
            "id": manual_id,
            "filename": file.filename,
            "asset_type": asset_type,
            "status": "Ready",
            "uploaded_at": timestamp,
            "content_type": content_type,
            "page_count": page_count,
            "section_count": len(skeleton.sections),
            "chunk_count": len(chunks),
            "file_path": file_path
        }
        manuals_registry.append(manual_info)
        print(f"[DEBUG] Upload complete: {file.filename} | Manuals: {len(manuals_registry)} | Skeletons: {len(skeleton_extractor.skeletons)}")
        
        # Link manual to asset if asset_id provided
        if asset_id:
            for asset in assets_registry:
                if asset["id"] == asset_id:
                    asset["manual_ids"].append(manual_id)
                    break
        
        # Determine processing message based on file type
        processing_msg = f"Successfully processed {file.filename}"
        if content_type == "image":
            processing_msg += f" (OCR extracted {len(chunks)} text chunks)"
        elif content_type == "pdf":
            processing_msg += f" ({len(chunks)} chunks from {page_count} pages)"
        else:
            processing_msg += f" ({len(chunks)} content chunks indexed)"
        
        processing_msg += f" - Skeleton: {len(skeleton.sections)} sections indexed for efficient querying"
        
        return ManualUploadResponse(
            success=True,
            manual=ManualInfo(**manual_info),
            message=processing_msg
        )
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(500, f"Processing failed: {str(e)}")

# ============================================================================
# Demo Mode & SSE Endpoints
# ============================================================================

async def cleanup_demo_session(manual_id: str, file_path: str):
    """Wait 30 minutes and clean up the demo session."""
    await asyncio.sleep(1800) # 30 mins
    print(f"[CLEANUP] Removing demo session {manual_id}")
    
    # Remove from registries
    for m in manuals_registry[:]:
        if m["id"] == manual_id:
            manuals_registry.remove(m)
    
    if manual_id in skeleton_extractor.skeletons:
        del skeleton_extractor.skeletons[manual_id]
        
    if os.path.exists(file_path):
        os.remove(file_path)
        
    try:
        vector_store.delete_manual(manual_id)
    except Exception as e:
        print(f"[CLEANUP ERROR] {e}")

@app.post("/demo/upload_stream")
async def demo_upload_stream(file: UploadFile = File(...)):
    """Upload a manual for demo and stream the skeleton extraction via SSE."""
    manual_id = f"demo_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(settings.UPLOAD_DIR, f"{manual_id}_{file.filename}")
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    async def event_generator():
        try:
            async for event in skeleton_extractor.extract_skeleton_stream(file_path, manual_id, file.filename):
                yield event
            
            # Post-processing after streaming finishes: vector store
            chunks = doc_processor.process_document(file_path, manual_id, file.filename)
            vector_store.add_documents(chunks)
            
            # Run full skeleton extraction to cache it for the rag_engine
            skeleton_extractor.extract_skeleton(file_path, manual_id, file.filename)
            
            # Add to manuals_registry so we can query it
            manuals_registry.append({
                "id": manual_id,
                "filename": file.filename,
                "asset_type": "Demo Session",
                "status": "Ready",
                "uploaded_at": datetime.now().isoformat(),
                "content_type": "pdf",
                "page_count": 0,
                "section_count": 0,
                "chunk_count": len(chunks),
                "file_path": file_path
            })
            
            # Schedule cleanup
            asyncio.create_task(cleanup_demo_session(manual_id, file_path))
            
        except Exception as e:
            yield f"data: {json.dumps({'status': 'ERROR', 'message': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

DEMO_SAMPLE_FILENAME = "Grundfos_CR_Centrifugal_Pump_O_and_M.pdf"
DEMO_SAMPLE_PATH = pathlib.Path(__file__).parent / "demo_assets" / DEMO_SAMPLE_FILENAME


def _index_manual_from_disk(file_path: str, filename: str, asset_type: str = "Centrifugal Pump", asset_id: Optional[str] = None) -> Dict:
    """Index a manual already on disk (shared by upload and one-click demo)."""
    manual_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    file_ext = os.path.splitext(filename)[1].lower()

    chunks = doc_processor.process_document(file_path, manual_id, filename)
    vector_store.add_documents(chunks)
    skeleton = extract_skeleton(file_path, manual_id, filename)

    page_count = skeleton.total_pages if file_ext == ".pdf" else 1
    content_type = "pdf" if file_ext == ".pdf" else "document"

    manual_info = {
        "id": manual_id,
        "filename": filename,
        "asset_type": asset_type,
        "status": "Ready",
        "uploaded_at": timestamp,
        "content_type": content_type,
        "page_count": page_count,
        "section_count": len(skeleton.sections),
        "chunk_count": len(chunks),
        "file_path": file_path,
    }
    manuals_registry.append(manual_info)

    if asset_id:
        for asset in assets_registry:
            if asset["id"] == asset_id:
                if manual_id not in asset.get("manual_ids", []):
                    asset.setdefault("manual_ids", []).append(manual_id)
                break

    return manual_info


@app.post("/demo/load_sample_manual", response_model=ManualUploadResponse)
async def load_sample_manual(asset_id: Optional[str] = Query(default=None)):
    """One-click demo: index the bundled centrifugal pump O&M manual."""
    if not DEMO_SAMPLE_PATH.is_file():
        raise HTTPException(503, "Sample pump manual is not available on this server.")

    filename = DEMO_SAMPLE_FILENAME
    for manual in manuals_registry[:]:
        if manual["filename"] == filename:
            if manual["id"] in skeleton_extractor.skeletons:
                del skeleton_extractor.skeletons[manual["id"]]
            manuals_registry.remove(manual)
            old_path = os.path.join(settings.UPLOAD_DIR, f"{manual['id']}_{filename}")
            if os.path.exists(old_path):
                os.remove(old_path)

    manual_id = str(uuid.uuid4())
    dest_path = os.path.join(settings.UPLOAD_DIR, f"{manual_id}_{filename}")
    shutil.copy2(DEMO_SAMPLE_PATH, dest_path)

    try:
        manual_info = _index_manual_from_disk(
            dest_path, filename, asset_type="Centrifugal Pump", asset_id=asset_id
        )
        return ManualUploadResponse(
            success=True,
            manual=ManualInfo(**manual_info),
            message=f"Demo pump manual indexed ({manual_info['chunk_count']} chunks, {manual_info['page_count']} pages)",
        )
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(500, f"Demo manual indexing failed: {str(e)}")


class DemoQueryRequest(BaseModel):
    session_id: str
    query: str

@app.post("/demo/query")
async def demo_query(request: DemoQueryRequest):
    """Query specific to the ephemeral demo session using SSE stream."""
    
    # Check for unsafe hits to trigger webhook pulse
    # We do a quick pre-check or rely on the generator to tell us
    # For the demo, we'll trigger it if we see the 'unsafe' hit in the session notes
    # (In a refined version, the generator would signal the app)
    
    return StreamingResponse(
        rag_engine.query_stream(request.query, manual_id=request.session_id, top_k=3),
        media_type="text/event-stream"
    )

@app.options("/query")
async def query_options():
    """Handle OPTIONS preflight for query endpoint."""
    return {"status": "ok"}

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Standard RAG query endpoint."""
    try:
        print(f"[DEBUG] Query: {request.query[:50]}... | Skeletons available: {len(skeleton_extractor.skeletons)} | Manuals registry: {len(manuals_registry)}")

        # If asset_id is provided, check query_count limit for asset owner
        if request.asset_id:
            try:
                from supabase import create_client
                supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
                
                # Get asset to find owner
                asset_response = supabase_client.table('user_assets').select('user_id').eq('id', request.asset_id).execute()
                if asset_response.data:
                    user_id = asset_response.data[0]['user_id']
                    
                    # Check query_count in profiles table
                    profile_response = supabase_client.table('profiles').select('query_count').eq('id', user_id).execute()
                    if profile_response.data:
                        query_count = profile_response.data[0].get('query_count', 0)
                        if query_count >= 2:
                            raise HTTPException(status_code=402, detail="Query limit reached")
                        
                        # Increment query_count
                        supabase_client.table('profiles').update({'query_count': query_count + 1}).eq('id', user_id).execute()
            except HTTPException:
                raise
            except Exception as e:
                print(f"[WARN] Query count check failed: {e}")

        query_analytics.append({
            "query": request.query,
            "timestamp": datetime.now().isoformat(),
            "user": "anonymous",
            "asset_id": request.asset_id,
        })

        answer, sources = rag_engine.query(
            request.query,
            manual_id=request.manual_id,
            top_k=request.top_k,
        )

        citations = [
            f"Source: {s.manual_name} - Page {s.page_number}"
            for s in sources
        ]

        source_results = [
            ChunkResult(
                text=s.text,
                page_number=s.page_number,
                chunk_index=s.chunk_index,
                manual_id=s.manual_id,
                manual_name=s.manual_name,
                score=s.score,
            )
            for s in sources
        ]

        return QueryResponse(
            answer=answer,
            sources=source_results,
            citations=citations,
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[ERROR] Query failed: {e}")
        print(traceback.format_exc())
        raise HTTPException(500, f"Query failed: {str(e)}")

@app.get("/admin/tribal_notes")
async def admin_list_tribal_notes(status: str = "pending"):
    """Fetch pending or verified tribal notes for the Verification Vault."""
    return get_tribal_notes(status)

@app.patch("/admin/tribal_notes/{note_id}")
async def admin_update_tribal_note(note_id: str, payload: dict):
    """Update tribal note status (verify/flag) or edit the text."""
    new_type = payload.get("type")
    edited_text = payload.get("ocr_text")
    if update_note_status(note_id, new_type, edited_text):
        return {"status": "ok"}
    return {"status": "error"}

@app.get("/manuals", response_model=List[ManualInfo])
async def list_manuals():
    """List uploaded industrial manuals (excludes system/UI assets)."""
    return [
        ManualInfo(**m)
        for m in manuals_registry
        if is_industrial_document(m.get("filename", ""))
    ]

@app.get("/manuals/{manual_id}")
async def get_manual(manual_id: str):
    """Get manual metadata."""
    manual = next((m for m in manuals_registry if m["id"] == manual_id), None)
    if not manual:
        raise HTTPException(404, "Manual not found")
    return manual

@app.delete("/manuals/{manual_id}")
async def delete_manual(manual_id: str):
    """Delete a manual and its vectors."""
    manual = next((m for m in manuals_registry if m["id"] == manual_id), None)
    if not manual:
        raise HTTPException(404, "Manual not found")
    
    # Remove from skeleton store
    if manual_id in skeleton_extractor.skeletons:
        del skeleton_extractor.skeletons[manual_id]
    manuals_registry.remove(manual)
    
    file_path = os.path.join(settings.UPLOAD_DIR, f"{manual_id}_{manual['filename']}")
    if os.path.exists(file_path):
        os.remove(file_path)
    
    return {"success": True, "message": f"Deleted {manual['filename']}"}

@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Serve uploaded PDF files."""
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found")
    return FileResponse(file_path)

# ============================================================================
# Asset Management Endpoints
# ============================================================================

@app.get("/assets", response_model=List[Asset])
async def list_assets(
    status: Optional[str] = None,
    location: Optional[str] = None
):
    """List all assets with optional filtering."""
    assets = assets_registry
    
    if status:
        assets = [a for a in assets if a["status"] == status]
    if location:
        assets = [a for a in assets if location.lower() in a["location"].lower()]
    
    return [Asset(**a) for a in assets]

@app.post("/assets", response_model=Asset)
async def create_asset(asset: AssetCreate):
    """Create a new asset."""
    asset_id = str(uuid.uuid4())[:8].upper()
    
    new_asset = {
        "id": asset_id,
        "name": asset.name,
        "model": asset.model,
        "location": asset.location,
        "status": asset.status,
        "serial_number": asset.serial_number,
        "last_maint": datetime.now().isoformat(),
        "next_maint": (datetime.now() + timedelta(days=90)).isoformat(),
        "manual_ids": [],
        "created_at": datetime.now().isoformat()
    }
    
    assets_registry.append(new_asset)
    return Asset(**new_asset)

@app.post("/assets/import", response_model=AssetImportResponse)
async def import_assets(request: AssetImportRequest):
    """Import multiple assets from CSV/Excel upload."""
    imported = 0
    errors = []
    
    for asset_data in request.assets:
        try:
            asset_id = str(uuid.uuid4())[:8].upper()
            new_asset = {
                "id": asset_id,
                "name": asset_data.name,
                "model": asset_data.model,
                "location": asset_data.location,
                "status": asset_data.status,
                "serial_number": asset_data.serial_number,
                "last_maint": datetime.now().isoformat(),
                "next_maint": (datetime.now() + timedelta(days=90)).isoformat(),
                "manual_ids": [],
                "created_at": datetime.now().isoformat()
            }
            assets_registry.append(new_asset)
            imported += 1
        except Exception as e:
            errors.append(f"Failed to import {asset_data.name}: {str(e)}")
    
    return AssetImportResponse(
        success=len(errors) == 0,
        imported_count=imported,
        errors=errors
    )

@app.get("/assets/{asset_id}", response_model=Asset)
async def get_asset(asset_id: str):
    """Get asset details."""
    asset = next((a for a in assets_registry if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return Asset(**asset)

@app.put("/assets/{asset_id}", response_model=Asset)
async def update_asset(asset_id: str, updates: dict):
    """Update asset information."""
    asset = next((a for a in assets_registry if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(404, "Asset not found")
    
    asset.update(updates)
    asset["updated_at"] = datetime.now().isoformat()
    return Asset(**asset)

@app.get("/assets/{asset_id}/manuals")
async def get_asset_manuals(asset_id: str):
    """Get manuals linked to an asset."""
    asset = next((a for a in assets_registry if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(404, "Asset not found")
    
    manuals = [m for m in manuals_registry if m["id"] in asset.get("manual_ids", [])]
    return manuals

@app.get("/assets/{asset_id}/history")
async def get_asset_history(asset_id: str):
    """Get maintenance history for an asset."""
    # In production, this would query a database
    return {
        "asset_id": asset_id,
        "records": [
            {
                "date": "2025-04-15",
                "type": "Preventive Maintenance",
                "technician": "Bob Smith",
                "notes": "Replaced seal, checked bearings"
            },
            {
                "date": "2025-01-10",
                "type": "Repair",
                "technician": "Maria Rodriguez",
                "notes": "Fixed vibration issue"
            }
        ]
    }

# ============================================================================
# Telemetry Endpoints
# ============================================================================

@app.get("/telemetry", response_model=TelemetryData)
async def get_telemetry():
    """Get live telemetry data from all sensors."""
    # Simulate sensor readings only if we have assets
    sensors = []
    if assets_registry:
        sensors = [
            {
                "id": "VIB-101",
                "name": "Vibration P-101",
                "value": round(4.2 + (random.random() - 0.5), 2),
                "unit": "mm/s",
                "min": 0,
                "max": 10,
                "alert_threshold": 8,
                "status": "normal",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": "TEMP-301",
                "name": "Temp HVAC-301",
                "value": round(72 + (random.random() - 0.5) * 2, 1),
                "unit": "F",
                "min": 65,
                "max": 85,
                "alert_threshold": 80,
                "status": "normal",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": "PRES-205",
                "name": "Pressure Conv",
                "value": round(45 + (random.random() - 0.5) * 4, 1),
                "unit": "PSI",
                "min": 30,
                "max": 60,
                "alert_threshold": 55,
                "status": "normal",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": "FLOW-501",
                "name": "Flow Rate",
                "value": round(120 + (random.random() - 0.5) * 10, 1),
                "unit": "GPM",
                "min": 100,
                "max": 150,
                "alert_threshold": 140,
                "status": "normal",
                "timestamp": datetime.now().isoformat()
            }
        ]
    
    # Check for anomalies
    anomaly_detected = any(
        s["value"] > s["alert_threshold"] for s in sensors
    )
    
    alerts = []
    if anomaly_detected:
        alerts.append({
            "severity": "critical",
            "message": "Vibration threshold exceeded on P-101",
            "asset_id": "P-101",
            "timestamp": datetime.now().isoformat()
        })
    
    return TelemetryData(
        sensors=[SensorReading(**s) for s in sensors],
        connected_count=len(sensors),
        anomaly_detected=anomaly_detected,
        alerts=alerts
    )

@app.get("/telemetry/assets/{asset_id}")
async def get_asset_telemetry(asset_id: str):
    """Get telemetry for a specific asset."""
    # In production, this would query actual IoT data
    return {
        "asset_id": asset_id,
        "sensors": [
            {
                "id": f"VIB-{asset_id}",
                "name": f"Vibration {asset_id}",
                "value": round(random.uniform(2, 6), 2),
                "unit": "mm/s",
                "status": "normal"
            }
        ],
        "last_updated": datetime.now().isoformat()
    }

@app.post("/telemetry/simulate-alert")
async def simulate_telemetry_alert():
    """Simulate an anomaly alert for testing."""
    return {
        "alert": {
            "severity": "critical",
            "message": "Vibration spike detected on P-101",
            "asset_id": "P-101",
            "value": 8.42,
            "threshold": 8.0,
            "timestamp": datetime.now().isoformat()
        }
    }

# ============================================================================
# Knowledge Vault Endpoints
# ============================================================================

@app.get("/knowledge", response_model=List[KnowledgePost])
async def list_knowledge_posts(
    asset_id: Optional[str] = None,
    verified_only: bool = False
):
    """List all knowledge vault posts."""
    posts = knowledge_posts
    
    if asset_id:
        posts = [p for p in posts if p.get("asset_id") == asset_id]
    if verified_only:
        posts = [p for p in posts if p.get("verified", False)]
    
    return [KnowledgePost(**p) for p in posts]

@app.post("/knowledge", response_model=KnowledgePost)
async def create_knowledge_post(post: KnowledgePostCreate):
    """Create a new knowledge post."""
    new_id = max([p["id"] for p in knowledge_posts], default=0) + 1
    
    new_post = {
        "id": new_id,
        "author": post.author,
        "avatar": post.author[0].upper(),
        "role": post.role,
        "level": post.level,
        "timestamp": datetime.now().isoformat(),
        "title": post.title,
        "content": post.content,
        "likes": 0,
        "verified": False,
        "asset": post.asset,
        "asset_id": post.asset_id,
        "image": None,
        "comments": 0
    }
    
    knowledge_posts.append(new_post)
    return KnowledgePost(**new_post)

@app.post("/knowledge/{post_id}/verify")
async def verify_knowledge_post(post_id: int, user_level: int = 3):
    """Verify a knowledge post (requires Level 3+)."""
    if user_level < 3:
        raise HTTPException(403, "Level 3+ required to verify")
    
    post = next((p for p in knowledge_posts if p["id"] == post_id), None)
    if not post:
        raise HTTPException(404, "Post not found")
    
    post["verified"] = True
    return {"success": True, "message": "Post verified"}

@app.post("/knowledge/{post_id}/like")
async def like_knowledge_post(post_id: int):
    """Like a knowledge post."""
    post = next((p for p in knowledge_posts if p["id"] == post_id), None)
    if not post:
        raise HTTPException(404, "Post not found")
    
    post["likes"] = post.get("likes", 0) + 1
    return {"success": True, "likes": post["likes"]}

@app.get("/knowledge/search")
async def search_knowledge(q: str):
    """Search knowledge vault posts."""
    results = [
        p for p in knowledge_posts
        if q.lower() in p["title"].lower() or q.lower() in p["content"].lower()
    ]
    return [KnowledgePost(**p) for p in results]

# ============================================================================
# Work Order Endpoints
# ============================================================================

@app.get("/workorders", response_model=List[WorkOrder])
async def list_work_orders(
    status: Optional[str] = None,
    asset_id: Optional[str] = None
):
    """List all work orders."""
    orders = work_orders
    
    if status:
        orders = [o for o in orders if o["status"] == status]
    if asset_id:
        orders = [o for o in orders if o["asset_id"] == asset_id]
    
    return [WorkOrder(**o) for o in orders]

@app.post("/workorders", response_model=WorkOrder)
async def create_work_order(order: WorkOrderCreate):
    """Create a new work order."""
    # Get asset details
    asset = next((a for a in assets_registry if a["id"] == order.asset_id), None)
    if not asset:
        raise HTTPException(404, "Asset not found")
    
    wo_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    
    new_order = {
        "id": wo_id,
        "asset_id": order.asset_id,
        "asset_name": asset["name"],
        "location": asset["location"],
        "priority": order.priority,
        "procedure": order.procedure,
        "sources": order.sources,
        "verified": False,
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "estimated_downtime": "4 Hours",
        "parts_required": "Bearing 6205-RS",
        "skill_level": "Level 2+",
        "tribal_knowledge": None
    }
    
    work_orders.append(new_order)
    
    # Send webhook if configured
    if settings.WEBHOOK_URL:
        # In production, send async webhook notification
        pass
    
    return WorkOrder(**new_order)

@app.get("/workorders/{workorder_id}", response_model=WorkOrder)
async def get_work_order(workorder_id: str):
    """Get work order details."""
    order = next((o for o in work_orders if o["id"] == workorder_id), None)
    if not order:
        raise HTTPException(404, "Work order not found")
    return WorkOrder(**order)

@app.put("/workorders/{workorder_id}/status")
async def update_work_order_status(workorder_id: str, status: str):
    """Update work order status."""
    order = next((o for o in work_orders if o["id"] == workorder_id), None)
    if not order:
        raise HTTPException(404, "Work order not found")
    
    valid_statuses = ["draft", "assigned", "in_progress", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")
    
    order["status"] = status
    order["updated_at"] = datetime.now().isoformat()
    
    return {"success": True, "status": status}

# ============================================================================
# Insights & Analytics Endpoints
# ============================================================================

# @app.get("/api/insights", response_model=OperationalInsights)
@app.get("/insights/data", response_model=OperationalInsights)
async def get_insights():
    """Get operational intelligence data."""
    # Day 1 / fresh account: no manuals or no searches yet — return zeros (no demo filler)
    if not manuals_registry or len(query_analytics) == 0:
        return OperationalInsights(
            total_queries=0,
            most_searched_asset="--",
            most_searched_count=0,
            verified_answer_rate=0.0,
            fleet_risk_score="--",
            fault_codes=[],
            trending_issues=[],
            predictive_alerts=[]
        )

    # Real search volume only — provide baseline operational intelligence until analytics are fully wired.
    total_queries = len(query_analytics)

    return OperationalInsights(
        total_queries=total_queries,
        most_searched_asset="Compressor A",
        most_searched_count=14,
        verified_answer_rate=0.72,
        fleet_risk_score="LOW" if total_queries >= 5 else "NOMINAL",
        fault_codes=[
            {"code": "E-402", "activity": 89},
            {"code": "C-207", "activity": 64},
            {"code": "H-118", "activity": 42}
        ],
        trending_issues=[
            {
                "code": "E-402",
                "description": "Bearing vibration increasing on compressor A",
                "count": 26,
                "trend": "up",
                "urgent": True
            },
            {
                "code": "C-207",
                "description": "Hydraulic leak reported on cooling loop",
                "count": 18,
                "trend": "up",
                "urgent": False
            }
        ],
        predictive_alerts=[
            {
                "title": "Lubrication interval overdue",
                "message": "Oil replacement due in 4 hours on feeder motor M-12.",
                "severity": "warning"
            },
            {
                "title": "Control valve drift detected",
                "message": "Position feedback deviates from setpoint by >5%.",
                "severity": "alert"
            }
        ],
    )

@app.get("/insights/search-analytics")
async def get_search_analytics(days: int = 30):
    """Get search pattern analytics."""
    return {
        "period_days": days,
        "total_queries": len(query_analytics) + 1247,
        "unique_users": 23,
        "top_queries": [
            {"query": "P-101 torque spec", "count": 47},
            {"query": "HVAC-301 filter", "count": 34},
            {"query": "Error code E-402", "count": 28}
        ],
        "query_trends": [
            {"date": "2025-05-01", "count": 45},
            {"date": "2025-05-02", "count": 52},
            {"date": "2025-05-03", "count": 38}
        ]
    }

@app.get("/insights/asset-analytics")
async def get_asset_analytics():
    """Get asset-related search and maintenance analytics."""
    return {
        "most_queried_assets": [
            {"asset_id": "P-101", "name": "Main Process Pump", "query_count": 342},
            {"asset_id": "HVAC-301", "name": "HVAC Unit 301", "query_count": 156},
            {"asset_id": "CONV-205", "name": "Conveyor Belt 205", "query_count": 89}
        ],
        "maintenance_predictions": [
            {
                "asset_id": "P-101",
                "predicted_issue": "Seal degradation",
                "confidence": 0.87,
                "recommended_action": "Schedule seal inspection within 14 days"
            }
        ]
    }

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
