#!/usr/bin/env python3
"""
IndexField RAG Backend Startup Script
Handles directory setup, dependency checks, and server launch.
"""

import os
import sys
import subprocess
import argparse

API_HOST = "0.0.0.0"
API_PORT = 8000

def ensure_directories():
    """Create necessary directories."""
    dirs = ["uploads", "chroma_db"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"[OK] Directory ready: {d}/")

def check_dependencies():
    """Verify Python dependencies are installed."""
    try:
        import fastapi
        import chromadb
        import fitz  # PyMuPDF
        import sentence_transformers
        print("[OK] Core dependencies verified")
        return True
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("[INFO] Run: pip install -r requirements.txt")
        return False

def check_ollama():
    """Check if Ollama is available for local LLM."""
    try:
        import ollama
        ollama.list()
        print("[OK] Ollama service detected")
        return True
    except Exception:
        print("[WARN] Ollama not available. LLM features will use fallback mode.")
        print("[INFO] Install Ollama from https://ollama.ai for full functionality")
        return False

def start_server(host=API_HOST, port=API_PORT, reload=False):
    """Start the FastAPI server."""
    print(f"\n{'='*50}")
    print(f"IndexField RAG API Server")
    print(f"{'='*50}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"API Docs: http://localhost:{port}/docs")
    print(f"API Base: http://localhost:{port}/")
    print(f"Dashboard: Open dashboard.html in your browser")
    print(f"{'='*50}\n")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main_enhanced:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[OK] Server stopped")

def main():
    parser = argparse.ArgumentParser(description="IndexField RAG Backend")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--port", type=int, default=API_PORT, help=f"Port (default: {API_PORT})")
    args = parser.parse_args()
    
    # Setup
    ensure_directories()
    
    # Temporarily skip dependency check due to VC++ Redistributable requirement
    # if not check_dependencies():
    #     sys.exit(1)
    pass
    
    check_ollama()
    
    # Start
    start_server(port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
