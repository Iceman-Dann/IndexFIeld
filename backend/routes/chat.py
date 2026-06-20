"""Chat and query routes."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ..middleware import get_user_context, check_sandbox_limits, format_error_response

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat queries."""
    query: str
    document_id: Optional[str] = None
    context: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat queries."""
    answer: str
    sources: List[Dict[str, Any]]
    query_count: int


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    context: dict = Depends(get_user_context)
):
    """
    Process a chat query against the RAG system.
    Checks sandbox limits before processing.
    """
    try:
        # Check sandbox limits
        if not await check_sandbox_limits(context, "query"):
            raise HTTPException(
                status_code=402,
                detail=format_error_response("QUERY_LIMIT_REACHED", "Query limit reached for sandbox account")
            )
        
        facility = context.get("facility")
        query_count = facility.get("query_count", 0) if facility else 0
        
        # TODO: Implement actual RAG query processing
        # For now, return a placeholder response
        
        return ChatResponse(
            answer="This is a placeholder response. The actual RAG implementation will be integrated here.",
            sources=[],
            query_count=query_count + 1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("CHAT_FAILED", "Chat query failed", str(e))
        )
