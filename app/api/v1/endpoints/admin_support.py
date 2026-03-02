from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.db.session import get_session
from app.schemas.admin_support import (
    AdminTicketListResponse, AdminTicketDetailResponse,
    TicketStatusUpdateAdmin, TicketAssignmentUpdate, TicketPriorityUpdate,
    InternalNoteCreate, AdminResponseCreate, BulkUpdateRequest,
    TicketTagsUpdate, AdminSupportStats, CannedResponseCreate,
    CannedResponseUpdate, CannedResponseResponse
)
from app.repositories.support_repository import SupportRepository
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.models.support import SupportTicket, SupportMessage

router = APIRouter()


@router.get("/tickets", response_model=AdminTicketListResponse)
async def get_all_tickets_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sla_breach: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all support tickets with advanced filtering (Admin only)
    
    Filters:
    - status: pending, active, resolved, closed
    - category: Payment, Technical, Account, Refund, General
    - priority: low, medium, high, urgent
    - assigned_to: UUID of admin user
    - search: Search in subject and messages
    - date_from/date_to: Date range filter
    - sla_breach: Filter tickets with SLA breach
    """
    skip = (page - 1) * limit
    support_repo = SupportRepository(session)
    
    # Build filters
    filters = {}
    if status:
        filters['status'] = status
    if category:
        filters['category'] = category
    if priority:
        filters['priority'] = priority
    if assigned_to:
        filters['assigned_to'] = assigned_to
    if sla_breach is not None:
        filters['sla_breach'] = sla_breach
    
    # Get tickets with filters
    tickets = await support_repo.get_all_tickets_admin(
        skip=skip,
        limit=limit,
        filters=filters,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        date_from=date_from,
        date_to=date_to
    )
    
    # Get total count
    total = await support_repo.count_tickets_admin(filters, search, date_from, date_to)
    
    return {
        "tickets": tickets,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


@router.get("/tickets/{ticket_id}", response_model=AdminTicketDetailResponse)
async def get_ticket_details_admin(
    ticket_id: UUID,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get detailed ticket information including messages and history (Admin only)"""
    support_repo = SupportRepository(session)
    
    # Get ticket with user info
    ticket = await support_repo.get_ticket_with_user(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Get messages (including internal notes)
    messages = await support_repo.get_messages_admin(ticket_id)
    
    # Get ticket history
    history = await support_repo.get_ticket_history(ticket_id)
    
    return {
        **ticket,
        "messages": messages,
        "history": history
    }


@router.put("/tickets/{ticket_id}/status")
async def update_ticket_status_admin(
    ticket_id: UUID,
    status_data: TicketStatusUpdateAdmin,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update ticket status with audit trail (Admin only)"""
    support_repo = SupportRepository(session)
    
    # Get current ticket
    ticket = await support_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    old_status = ticket.status
    
    # Update status
    updated_ticket = await support_repo.update_ticket_status(
        ticket_id=ticket_id,
        status=status_data.status,
        admin_id=current_user.id,
        notes=status_data.notes
    )
    
    # Log history
    await support_repo.add_ticket_history(
        ticket_id=ticket_id,
        admin_id=current_user.id,
        action="status_changed",
        old_value=old_status,
        new_value=status_data.status,
        notes=status_data.notes
    )
    
    return updated_ticket


@router.put("/tickets/{ticket_id}/assign")
async def assign_ticket_admin(
    ticket_id: UUID,
    assignment_data: TicketAssignmentUpdate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Assign ticket to admin user (Admin only)"""
    support_repo = SupportRepository(session)
    
    # Get current ticket
    ticket = await support_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    old_assigned = ticket.assigned_to
    
    # Update assignment
    updated_ticket = await support_repo.assign_ticket(
        ticket_id=ticket_id,
        assigned_to=assignment_data.assigned_to,
        admin_id=current_user.id
    )
    
    # Log history
    await support_repo.add_ticket_history(
        ticket_id=ticket_id,
        admin_id=current_user.id,
        action="assigned",
        old_value=str(old_assigned) if old_assigned else None,
        new_value=str(assignment_data.assigned_to) if assignment_data.assigned_to else None,
        notes=assignment_data.notes
    )
    
    return updated_ticket


@router.put("/tickets/{ticket_id}/priority")
async def update_ticket_priority_admin(
    ticket_id: UUID,
    priority_data: TicketPriorityUpdate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update ticket priority (Admin only)"""
    support_repo = SupportRepository(session)
    
    # Get current ticket
    ticket = await support_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    old_priority = ticket.priority
    
    # Update priority
    updated_ticket = await support_repo.update_ticket_priority(
        ticket_id=ticket_id,
        priority=priority_data.priority,
        admin_id=current_user.id
    )
    
    # Log history
    await support_repo.add_ticket_history(
        ticket_id=ticket_id,
        admin_id=current_user.id,
        action="priority_changed",
        old_value=old_priority,
        new_value=priority_data.priority,
        notes=priority_data.notes
    )
    
    return updated_ticket


@router.post("/tickets/{ticket_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_internal_note(
    ticket_id: UUID,
    note_data: InternalNoteCreate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Add internal note to ticket (visible only to admins)"""
    support_repo = SupportRepository(session)
    
    # Verify ticket exists
    ticket = await support_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Add internal note
    note = await support_repo.add_internal_note(
        ticket_id=ticket_id,
        admin_id=current_user.id,
        content=note_data.content,
        attachments=note_data.attachments
    )
    
    return note


@router.post("/tickets/{ticket_id}/respond", status_code=status.HTTP_201_CREATED)
async def send_admin_response(
    ticket_id: UUID,
    response_data: AdminResponseCreate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Send response to user (Admin only)"""
    support_repo = SupportRepository(session)
    
    # Verify ticket exists
    ticket = await support_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Add response message
    message = await support_repo.add_message(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        sender_type="admin",
        content=response_data.content,
        attachments=response_data.attachments
    )
    
    # Update first_response_at if this is the first admin response (if column exists)
    if hasattr(ticket, 'first_response_at') and not ticket.first_response_at:
        await support_repo.update_first_response(ticket_id)
    
    # Update status if requested
    if response_data.update_status:
        await support_repo.update_ticket_status(
            ticket_id=ticket_id,
            status=response_data.update_status,
            admin_id=current_user.id
        )
    
    return message


@router.post("/tickets/bulk-update")
async def bulk_update_tickets(
    bulk_data: BulkUpdateRequest,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Bulk update multiple tickets (Admin only)"""
    support_repo = SupportRepository(session)
    
    results = []
    updated_count = 0
    failed_count = 0
    
    for ticket_id in bulk_data.ticket_ids:
        try:
            if bulk_data.action == "assign":
                await support_repo.assign_ticket(
                    ticket_id=ticket_id,
                    assigned_to=UUID(bulk_data.value) if bulk_data.value else None,
                    admin_id=current_user.id
                )
            elif bulk_data.action == "status":
                await support_repo.update_ticket_status(
                    ticket_id=ticket_id,
                    status=bulk_data.value,
                    admin_id=current_user.id,
                    notes=bulk_data.notes
                )
            elif bulk_data.action == "priority":
                await support_repo.update_ticket_priority(
                    ticket_id=ticket_id,
                    priority=bulk_data.value,
                    admin_id=current_user.id
                )
            
            results.append({"ticket_id": str(ticket_id), "success": True})
            updated_count += 1
        except Exception as e:
            results.append({"ticket_id": str(ticket_id), "success": False, "error": str(e)})
            failed_count += 1
    
    return {
        "updated": updated_count,
        "failed": failed_count,
        "results": results
    }


@router.post("/tickets/{ticket_id}/tags")
async def update_ticket_tags(
    ticket_id: UUID,
    tags_data: TicketTagsUpdate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Add or remove tags from ticket (Admin only)"""
    support_repo = SupportRepository(session)
    
    # Get current ticket
    ticket = await support_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Update tags
    updated_ticket = await support_repo.update_ticket_tags(
        ticket_id=ticket_id,
        action=tags_data.action,
        tags=tags_data.tags
    )
    
    return updated_ticket


@router.get("/stats", response_model=AdminSupportStats)
async def get_support_statistics(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    admin_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get comprehensive support statistics (Admin only)"""
    support_repo = SupportRepository(session)
    
    stats = await support_repo.get_admin_stats(
        date_from=date_from,
        date_to=date_to,
        admin_id=admin_id
    )
    
    return stats


@router.get("/tickets/export")
async def export_tickets(
    format: str = Query("csv", regex="^(csv|json)$"),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Export tickets to CSV or JSON (Admin only)"""
    support_repo = SupportRepository(session)
    
    # Build filters
    filters = {}
    if status:
        filters['status'] = status
    if category:
        filters['category'] = category
    
    # Get all tickets matching filters
    tickets = await support_repo.get_all_tickets_admin(
        skip=0,
        limit=10000,  # Large limit for export
        filters=filters,
        date_from=date_from,
        date_to=date_to
    )
    
    if format == "csv":
        # Generate CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'User Email', 'Subject', 'Category', 'Priority', 
            'Status', 'Created At', 'Resolved At'
        ])
        
        # Write data
        for ticket in tickets:
            writer.writerow([
                str(ticket['id']),
                ticket.get('user_email', ''),
                ticket['subject'],
                ticket['category'],
                ticket['priority'],
                ticket['status'],
                ticket['created_at'],
                ticket.get('resolved_at', '')
            ])
        
        from fastapi.responses import StreamingResponse
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=tickets_export_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    else:
        # Return JSON
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content={"tickets": tickets},
            headers={
                "Content-Disposition": f"attachment; filename=tickets_export_{datetime.now().strftime('%Y%m%d')}.json"
            }
        )


# Canned Responses Endpoints

@router.get("/canned-responses", response_model=List[CannedResponseResponse])
async def get_canned_responses(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get all canned responses (Admin only)"""
    support_repo = SupportRepository(session)
    responses = await support_repo.get_canned_responses(category=category)
    return responses


@router.post("/canned-responses", response_model=CannedResponseResponse, status_code=status.HTTP_201_CREATED)
async def create_canned_response(
    response_data: CannedResponseCreate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Create canned response (Admin only)"""
    support_repo = SupportRepository(session)
    
    response = await support_repo.create_canned_response(
        title=response_data.title,
        content=response_data.content,
        category=response_data.category,
        shortcut=response_data.shortcut,
        created_by=current_user.id
    )
    
    return response


@router.put("/canned-responses/{response_id}", response_model=CannedResponseResponse)
async def update_canned_response(
    response_id: UUID,
    response_data: CannedResponseUpdate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update canned response (Admin only)"""
    support_repo = SupportRepository(session)
    
    response = await support_repo.update_canned_response(
        response_id=response_id,
        **response_data.model_dump(exclude_unset=True)
    )
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canned response not found"
        )
    
    return response


@router.delete("/canned-responses/{response_id}")
async def delete_canned_response(
    response_id: UUID,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Delete canned response (Admin only)"""
    support_repo = SupportRepository(session)
    
    success = await support_repo.delete_canned_response(response_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canned response not found"
        )
    
    return {"message": "Canned response deleted successfully"}
