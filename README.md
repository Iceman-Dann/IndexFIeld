# IndexField RAG Core

The Document Playground — A sovereign RAG system for industrial technical documentation.

## Quick Start (10-Second Test)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the backend
python start_backend.py

# 3. Open the dashboard
# In another terminal or browser:
# Open dashboard.html directly, or serve with:
python -m http.server 3000
# Then visit http://localhost:3000/dashboard.html
```

## What You Get

1. **Document Playground** (`dashboard.html`)
   - Technical console interface with search
   - Two-column layout: AI answer + PDF viewer
   - Click any citation to auto-scroll to source page
   - Liability badges showing manual name and page number

2. **Manuals Manager**
   - Upload PDFs (drag & drop or file picker)
   - Asset type classification (HVAC, Turbine, Conveyor, etc.)
   - Status tracking (Indexing → Ready)
   - Page and chunk counts

3. **RAG Pipeline** (Python/FastAPI)
   - `POST /upload` — Process PDF into vector embeddings
   - `POST /query` — Retrieve context + generate answers
   - ChromaDB for local vector storage
   - Sentence-transformers for embeddings
   - Ollama integration for local LLM (Llama 3.2)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DASHBOARD (HTML/JS)                        │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ Search Input │  │  AI Answer Panel │  │  PDF Viewer    │  │
│  └──────────────┘  └─────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ HTTP
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND                             │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  /upload    │  │  Document    │  │   Vector Store     │  │
│  │  /query     │──│  Processor   │──│   (ChromaDB)       │  │
│  │  /manuals   │  │  (PyMuPDF)   │  │   (embeddings)     │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
│                           │                                  │
│                    ┌──────┴──────┐                          │
│                    │  RAG Engine │──┐ Ollama (local LLM)     │
│                    └─────────────┘  │                        │
└─────────────────────────────────────┴────────────────────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/upload` | POST | Upload PDF with `file` and `asset_type` |
| `/query` | POST | Query with `query`, optional `manual_id` |
| `/manuals` | GET | List all uploaded manuals |
| `/manuals/{id}` | DELETE | Remove manual and vectors |

## The 10-Second Test

1. **Sign in** at `signin.html` (demo mode, any credentials)
2. **Upload a manual** in the Manuals Manager tab
3. **Ask a question** in the Query Console:
   - "What is the torque spec for bearing 6205?"
   - "Show me the wiring diagram for pump P-101"
4. **Verify citations** — Answer includes "Source: [Manual] - Page [N]"
5. **Click citations** — PDF viewer jumps to that page

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **RAG Orchestration**: LangChain patterns (custom implementation)
- **PDF Extraction**: PyMuPDF (fitz)
- **Vector DB**: ChromaDB (local, sovereign)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM**: Ollama + Llama 3.2 (local, no API keys)
- **Frontend**: Vanilla HTML/JS, Tailwind CSS, FontAwesome

## File Structure

```
IndexField/
├── index.html              # Landing page
├── signin.html             # Authentication page
├── dashboard.html          # Document Playground UI
├── requirements.txt        # Python dependencies
├── start_backend.py        # Backend launcher
├── backend/
│   ├── main.py            # FastAPI app, endpoints
│   ├── document_processor.py  # PDF → chunks
│   ├── vector_store.py    # ChromaDB interface
│   └── rag_engine.py      # Retrieval + Generation
├── uploads/               # PDF storage (created on run)
└── chroma_db/             # Vector database (created on run)
```

## Configuration

No configuration needed for local development. All data stays local:
- PDFs in `uploads/`
- Vectors in `chroma_db/`
- LLM via Ollama on localhost:11434

## Optional: Ollama Setup

For best results, install Ollama and pull Llama 3.2:

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download/windows

# Pull the model
ollama pull llama3.2
```

If Ollama is not available, the system falls back to showing raw retrieved chunks.

## Next Steps for Production

1. **Authentication**: Replace demo auth with JWT/SSO
2. **Database**: Replace in-memory manual registry with PostgreSQL
3. **Storage**: Move uploads to S3/MinIO with encryption
4. **LLM**: Add OpenAI/Anthropic as optional remote provider
5. **Deployment**: Docker + Kubernetes manifest

## License

Proprietary - IndexField Industrial Intelligence Platform
