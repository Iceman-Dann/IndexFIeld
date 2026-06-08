# IndexField API Reference

Complete API documentation for the IndexField Industrial Intelligence Platform.

## Base URL
```
http://localhost:8000
```

## Health & Status

### GET /health
System health check endpoint.

**Response:**
```json
{
  "vector_db": "Online",
  "llm": "llama3.2",
  "ollama_running": true,
  "model_available": true,
  "manuals_count": 5,
  "assets_count": 156,
  "uptime_seconds": 0
}
```

---

## Authentication

### POST /auth/login
Authenticate and get JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### GET /auth/verify
Verify JWT token validity.

**Headers:**
```
Authorization: Bearer <token>
```

---

## RAG & Document Query

### POST /query
Query the RAG system for answers with citations.

**Request:**
```json
{
  "query": "What is the torque spec for bearing 6205?",
  "manual_id": null,
  "top_k": 3
}
```

**Response:**
```json
{
  "answer": "The torque specification for bearing 6205 is...",
  "sources": [
    {
      "text": "Bearing 6205 requires torque of 45 Nm...",
      "page_number": 42,
      "chunk_index": 5,
      "manual_id": "uuid",
      "manual_name": "pump_manual.pdf",
      "score": 0.95
    }
  ],
  "citations": ["Source: pump_manual.pdf - Page 42"]
}
```

---

## Manual Upload & Management

### POST /upload
Upload and process a PDF manual.

**Request:**
- Content-Type: multipart/form-data
- Fields:
  - `file`: PDF file
  - `asset_type`: String (default: "Industrial Equipment")
  - `asset_id`: Optional asset ID to link manual

**Response:**
```json
{
  "success": true,
  "manual": {
    "id": "uuid",
    "filename": "pump_manual.pdf",
    "asset_type": "Industrial Equipment",
    "status": "Ready",
    "uploaded_at": "2025-05-06T16:00:00",
    "page_count": 150,
    "chunk_count": 450
  },
  "message": "Successfully processed pump_manual.pdf into 450 chunks"
}
```

### GET /manuals
List all uploaded manuals.

**Response:**
```json
[
  {
    "id": "uuid",
    "filename": "pump_manual.pdf",
    "asset_type": "Industrial Equipment",
    "status": "Ready",
    "uploaded_at": "2025-05-06T16:00:00",
    "page_count": 150,
    "chunk_count": 450
  }
]
```

### GET /manuals/{manual_id}
Get specific manual details.

### DELETE /manuals/{manual_id}
Delete a manual and its vectors.

### GET /uploads/{filename}
Serve uploaded PDF file.

---

## Asset Management (Digital Twins)

### GET /assets
List all assets with optional filtering.

**Query Parameters:**
- `status`: Filter by status (online, offline, warning, maintenance)
- `location`: Filter by location

**Response:**
```json
[
  {
    "id": "P-101",
    "name": "Main Process Pump P-101",
    "model": "Grundfos CR 95",
    "location": "Building A - Floor 2",
    "status": "online",
    "last_maint": "2025-04-15",
    "next_maint": "2025-07-15",
    "serial_number": "P101-2024-0892",
    "manual_ids": [],
    "created_at": "2025-01-01T00:00:00"
  }
]
```

### POST /assets
Create a new asset.

**Request:**
```json
{
  "name": "New Pump",
  "model": "Grundfos CR 95",
  "location": "Building B - Floor 1",
  "status": "online",
  "serial_number": "ABC-123"
}
```

### POST /assets/import
Import multiple assets.

**Request:**
```json
{
  "assets": [
    {
      "name": "Pump 1",
      "model": "Model A",
      "location": "Building A",
      "status": "online"
    }
  ]
}
```

### GET /assets/{asset_id}
Get asset details.

### PUT /assets/{asset_id}
Update asset information.

### GET /assets/{asset_id}/manuals
Get manuals linked to an asset.

### GET /assets/{asset_id}/history
Get maintenance history for an asset.

---

## Live Telemetry

### GET /telemetry
Get live telemetry data from all sensors.

**Response:**
```json
{
  "sensors": [
    {
      "id": "VIB-101",
      "name": "Vibration P-101",
      "value": 4.2,
      "unit": "mm/s",
      "min": 0,
      "max": 10,
      "alert_threshold": 8,
      "status": "normal",
      "timestamp": "2025-05-06T16:00:00"
    }
  ],
  "connected_count": 4,
  "anomaly_detected": false,
  "alerts": []
}
```

### GET /telemetry/assets/{asset_id}
Get telemetry for a specific asset.

### POST /telemetry/simulate-alert
Simulate an anomaly alert for testing.

---

## Knowledge Vault

### GET /knowledge
List all knowledge vault posts.

**Query Parameters:**
- `asset_id`: Filter by asset
- `verified_only`: Only show verified posts

**Response:**
```json
[
  {
    "id": 1,
    "author": "Senior Tech Bob",
    "avatar": "B",
    "role": "Level 3 Technician",
    "level": 3,
    "timestamp": "2025-04-28",
    "title": "P-101 Seal Replacement Shortcut",
    "content": "The manual says to drain the entire system...",
    "likes": 12,
    "verified": true,
    "asset": "P-101",
    "asset_id": "P-101",
    "comments": 3
  }
]
```

### POST /knowledge
Create a new knowledge post.

**Request:**
```json
{
  "author": "John Doe",
  "role": "Level 2 Technician",
  "level": 2,
  "title": "Quick Fix for Filter",
  "content": "Reset the sensor by holding TEST for 5 seconds",
  "asset": "HVAC-301",
  "asset_id": "HVAC-301"
}
```

### POST /knowledge/{post_id}/verify
Verify a knowledge post (requires Level 3+).

**Query Parameters:**
- `user_level`: User's technician level

### POST /knowledge/{post_id}/like
Like a knowledge post.

### GET /knowledge/search
Search knowledge vault posts.

**Query Parameters:**
- `q`: Search query

---

## Work Orders

### GET /workorders
List all work orders.

**Query Parameters:**
- `status`: Filter by status
- `asset_id`: Filter by asset

**Response:**
```json
[
  {
    "id": "WO-20250506-A1B2",
    "asset_id": "P-101",
    "asset_name": "Main Process Pump P-101",
    "location": "Building A - Floor 2",
    "priority": "CRITICAL",
    "procedure": "Inspect bearing housing...",
    "sources": ["Manual p.42"],
    "verified": false,
    "status": "draft",
    "created_at": "2025-05-06T16:00:00",
    "estimated_downtime": "4 Hours",
    "parts_required": "Bearing 6205-RS",
    "skill_level": "Level 2+",
    "tribal_knowledge": null
  }
]
```

### POST /workorders
Create a new work order.

**Request:**
```json
{
  "asset_id": "P-101",
  "priority": "HIGH",
  "procedure": "Anomaly detected - inspection required",
  "sources": ["AI Anomaly Detection"],
  "anomaly_type": "Vibration Spike"
}
```

### GET /workorders/{workorder_id}
Get work order details.

### PUT /workorders/{workorder_id}/status
Update work order status.

**Query Parameters:**
- `status`: New status (draft, assigned, in_progress, completed, cancelled)

---

## Operational Intelligence

### GET /insights
Get operational intelligence data.

**Response:**
```json
{
  "total_queries": 1247,
  "most_searched_asset": "Pump P-101",
  "most_searched_count": 342,
  "verified_answer_rate": 0.89,
  "fleet_risk_score": "MEDIUM",
  "fault_codes": [
    {
      "code": "E-100",
      "activity": 45,
      "criticality": "medium"
    }
  ],
  "trending_issues": [
    {
      "code": "E-402",
      "description": "Pump P-101 Seal Leak",
      "count": 47,
      "trend": "up",
      "urgent": true
    }
  ],
  "predictive_alerts": [
    {
      "severity": "warning",
      "title": "Pump Seal Failures Trending",
      "message": "47 searches for 'P-101 seal leak' in 7 days..."
    }
  ]
}
```

### GET /insights/search-analytics
Get search pattern analytics.

**Query Parameters:**
- `days`: Number of days (default: 30)

### GET /insights/asset-analytics
Get asset-related analytics.

---

## Environment Variables

All configuration is managed through the `.env` file:

### Server
- `API_HOST`: Server host (default: 0.0.0.0)
- `API_PORT`: Server port (default: 8000)
- `DEBUG`: Debug mode (default: false)

### AI/LLM (Gemini 1.5 Flash Primary)
- `GEMINI_API_KEY`: Google Gemini API key (**required for primary LLM**)
- `GEMINI_MODEL`: Primary model (default: gemini-1.5-flash)
- `GEMINI_FALLBACK_MODEL`: Fallback model (default: gemini-1.5-pro)
- `OLLAMA_BASE_URL`: Ollama server URL (fallback)
- `OLLAMA_MODEL`: Local fallback model (default: llama3.2)
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)

### Database
- `DATABASE_URL`: Database connection string
- `CHROMA_DB_PATH`: ChromaDB storage path

### Authentication
- `JWT_SECRET_KEY`: JWT signing key
- `ADMIN_USERNAME`: Admin username
- `ADMIN_PASSWORD_HASH`: Bcrypt hashed password

### Feature Flags
- `ENABLE_TELEMETRY`: Enable telemetry features
- `ENABLE_KNOWLEDGE_VAULT`: Enable knowledge vault
- `ENABLE_WORK_ORDERS`: Enable work order management
- `ENABLE_ANOMALY_DETECTION`: Enable AI anomaly detection

---

## Running the Backend

### Installation
```bash
cd c:\Users\nvx76\OneDrive\Desktop\IndexField
pip install -r requirements.txt
```

### Configure Gemini API Key
Edit `.env` file and add your Gemini API key:
```
GEMINI_API_KEY=your-actual-api-key-here
```

Get your API key from: https://makersuite.google.com/app/apikey

### Optional: Start Ollama (fallback if Gemini unavailable)
```bash
ollama serve
ollama pull llama3.2
```

### Start Backend
```bash
cd backend
python main_enhanced.py
```

Or with uvicorn directly:
```bash
uvicorn backend.main_enhanced:app --host 0.0.0.0 --port 8000 --reload
```

---

## Dashboard Integration

The dashboard.html automatically connects to these endpoints when loaded. Simply open the dashboard in a browser while the backend is running on port 8000.

All API calls use the base URL: `http://localhost:8000`
