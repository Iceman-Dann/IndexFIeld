"""Work order management routes."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from ..middleware import get_user_context, check_sandbox_limits, format_error_response
from ..config import get_settings
from supabase import create_client

router = APIRouter(prefix="/api/workorders", tags=["workorders"])
settings = get_settings()
supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
supabase = create_client(settings.SUPABASE_URL, supabase_key)


class WorkOrderCreateRequest(BaseModel):
    """Request model for creating a work order."""
    title: str
    description: str
    asset_id: Optional[str] = None
    priority: str = "medium"
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


class WorkOrderResponse(BaseModel):
    """Response model for work order data."""
    id: str
    title: str
    description: str
    asset_id: Optional[str]
    priority: str
    status: str
    assigned_to: Optional[str]
    due_date: Optional[str]
    created_at: str
    updated_at: str


@router.get("/", response_model=List[WorkOrderResponse])
async def list_work_orders(context: dict = Depends(get_user_context)):
    """List all work orders for the user's facility."""
    facility_id = context.get("facility_id")
    user_id = context["user_id"]
    role = context.get("role")
    
    if not facility_id:
        # Demo users without a facility see an empty list rather than an error
        return []
    
    try:
        # Build query based on role
        query = supabase.table("work_orders").select("*").eq("facility_id", facility_id)
        
        # Technicians only see work orders assigned to them
        if role == "technician":
            query = query.eq("assigned_to", user_id)
        
        response = query.execute()
        
        work_orders = [
            WorkOrderResponse(
                id=wo["id"],
                title=wo["title"],
                description=wo["description"],
                asset_id=wo.get("asset_id"),
                priority=wo.get("priority", "medium"),
                status=wo.get("status", "open"),
                assigned_to=wo.get("assigned_to"),
                due_date=wo.get("due_date"),
                created_at=wo["created_at"],
                updated_at=wo["updated_at"]
            )
            for wo in response.data
        ]
        
        return work_orders
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("WORKORDERS_LIST_FAILED", "Failed to list work orders", str(e))
        )


@router.post("/create", response_model=WorkOrderResponse)
async def create_work_order(
    work_order_data: WorkOrderCreateRequest,
    context: dict = Depends(get_user_context)
):
    """Create a new work order."""
    facility_id = context.get("facility_id")
    user_id = context["user_id"]
    
    if not facility_id:
        raise HTTPException(
            status_code=400,
            detail="No facility associated with user"
        )
    
    try:
        # Check sandbox limits (max 2 work orders for sandbox)
        facility = context.get("facility")
        if facility and facility.get("account_type") == "sandbox":
            # Count current work orders
            count_response = supabase.table("work_orders").select("*", count="exact").eq("facility_id", facility_id).execute()
            if count_response.count and count_response.count >= 2:
                raise HTTPException(
                    status_code=402,
                    detail=format_error_response("WORKORDER_LIMIT_REACHED", "Work order limit reached for sandbox account")
                )
        
        work_order_id = str(uuid.uuid4())
        
        work_order_record = {
            "id": work_order_id,
            "facility_id": facility_id,
            "user_id": user_id,
            "title": work_order_data.title,
            "description": work_order_data.description,
            "asset_id": work_order_data.asset_id,
            "priority": work_order_data.priority,
            "assigned_to": work_order_data.assigned_to,
            "due_date": work_order_data.due_date,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("work_orders").insert(work_order_record).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create work order"
            )
        
        return WorkOrderResponse(**response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("WORKORDER_CREATE_FAILED", "Failed to create work order", str(e))
        )


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
async def get_work_order(
    work_order_id: str,
    context: dict = Depends(get_user_context)
):
    """Get a specific work order."""
    facility_id = context.get("facility_id")
    
    if not facility_id:
        raise HTTPException(
            status_code=400,
            detail="No facility associated with user"
        )
    
    try:
        response = supabase.table("work_orders").select("*").eq("id", work_order_id).eq("facility_id", facility_id).single()
        
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Work order not found or access denied"
            )
        
        return WorkOrderResponse(**response.data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("WORKORDER_GET_FAILED", "Failed to get work order", str(e))
        )


@router.patch("/{work_order_id}")
async def update_work_order(
    work_order_id: str,
    work_order_data: Dict[str, Any],
    context: dict = Depends(get_user_context)
):
    """Update a work order."""
    facility_id = context.get("facility_id")
    user_id = context["user_id"]
    role = context.get("role")
    
    if not facility_id:
        raise HTTPException(
            status_code=400,
            detail="No facility associated with user"
        )
    
    try:
        # Check permissions for status changes
        if "status" in work_order_data:
            # Only owners and supervisors can change status to resolved/closed
            if work_order_data["status"] in ["resolved", "closed"] and role not in ["owner", "supervisor"]:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions to change work order status"
                )
        
        # Build update dict with only allowed fields
        allowed_fields = [
            "title", "description", "asset_id", "priority",
            "assigned_to", "due_date", "status"
        ]
        
        update_data = {k: v for k, v in work_order_data.items() if k in allowed_fields}
        update_data["updated_at"] = datetime.now().isoformat()
        
        if not update_data or len(update_data) == 1:  # Only updated_at
            raise HTTPException(
                status_code=400,
                detail="No valid fields to update"
            )
        
        supabase.table("work_orders").update(update_data).eq("id", work_order_id).eq("facility_id", facility_id).execute()
        
        return {"success": True, "message": "Work order updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("WORKORDER_UPDATE_FAILED", "Failed to update work order", str(e))
        )


@router.delete("/{work_order_id}")
async def delete_work_order(
    work_order_id: str,
    context: dict = Depends(get_user_context)
):
    """Delete a work order."""
    facility_id = context.get("facility_id")
    role = context.get("role")
    
    if not facility_id:
        raise HTTPException(
            status_code=400,
            detail="No facility associated with user"
        )
    
    # Only owners can delete work orders
    if role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to delete work orders"
        )
    
    try:
        # Check if work order belongs to user's facility
        response = supabase.table("work_orders").select("*").eq("id", work_order_id).eq("facility_id", facility_id).single()
        
        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Work order not found or access denied"
            )
        
        # Delete work order
        supabase.table("work_orders").delete().eq("id", work_order_id).execute()
        
        return {"success": True, "message": "Work order deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response("WORKORDER_DELETE_FAILED", "Failed to delete work order", str(e))
        )
