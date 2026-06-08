from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from datetime import datetime
import json

from backend.document_processor import DocumentProcessor
from backend.vector_store import VectorStore
from backend.rag_engine import RAGEngine
from backend.document_skeleton import SkeletonExtractor

app = FastAPI(title="IndexField RAG API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize components
doc_processor = DocumentProcessor()
vector_store = VectorStore()
skeleton_extractor = SkeletonExtractor()
rag_engine = RAGEngine(skeleton_extractor)

# In-memory manual registry (replace with DB in production)
manuals_registry = []

# --- Models ---
class QueryRequest(BaseModel):
    query: str
    manual_id: Optional[str] = None
    top_k: int = 3
    context: Optional[str] = None  # Pasted text or additional context

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
    status: str
    uploaded_at: str
    page_count: int
    chunk_count: int

class ManualUploadResponse(BaseModel):
    success: bool
    manual: ManualInfo
    message: str

# --- Endpoints ---
@app.get("/")
async def root():
    return {"status": "IndexField RAG API Operational", "version": "1.0.0"}

@app.post("/upload", response_model=ManualUploadResponse)
async def upload_manual(
    file: UploadFile = File(...),
    asset_type: str = Query(default="Industrial Equipment")
):
    """Upload and process a PDF manual."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")
    
    manual_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{manual_id}_{file.filename}")
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Process document
    try:
        chunks = doc_processor.process_pdf(file_path, manual_id, file.filename)
        
        # Store in vector DB
        vector_store.add_documents(chunks)
        
        # Register manual
        manual_info = ManualInfo(
            id=manual_id,
            filename=file.filename,
            asset_type=asset_type,
            status="Ready",
            uploaded_at=timestamp,
            page_count=max(c.page_number for c in chunks) if chunks else 0,
            chunk_count=len(chunks)
        )
        manuals_registry.append(manual_info)
        
        return ManualUploadResponse(
            success=True,
            manual=manual_info,
            message=f"Successfully processed {file.filename} into {len(chunks)} chunks"
        )
        
    except Exception as e:
        # Cleanup on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(500, f"Processing failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the RAG system for answers with citations."""
    try:
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
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            citations=citations
        )
    except Exception as e:
        raise HTTPException(500, f"Query failed: {str(e)}")

@app.get("/manuals", response_model=List[ManualInfo])
async def list_manuals():
    """List all uploaded manuals with status."""
    return manuals_registry

@app.get("/manuals/{manual_id}")
async def get_manual(manual_id: str):
    """Get manual metadata."""
    manual = next((m for m in manuals_registry if m.id == manual_id), None)
    if not manual:
        raise HTTPException(404, "Manual not found")
    return manual

@app.delete("/manuals/{manual_id}")
async def delete_manual(manual_id: str):
    """Delete a manual and its vectors."""
    manual = next((m for m in manuals_registry if m.id == manual_id), None)
    if not manual:
        raise HTTPException(404, "Manual not found")
    
    # Remove from vector store
    vector_store.delete_manual(manual_id)
    
    # Remove from registry
    manuals_registry.remove(manual)
    
    # Remove file
    file_path = os.path.join(UPLOAD_DIR, f"{manual_id}_{manual.filename}")
    if os.path.exists(file_path):
        os.remove(file_path)
    
    return {"success": True, "message": f"Deleted {manual.filename}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
