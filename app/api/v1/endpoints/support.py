from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.support import (
    SupportTicketCreate, SupportTicketResponse, SupportMessageCreate,
    TicketStatusUpdate, TicketAssignUpdate, FAQResponse, FAQCreate, FAQUpdate,
    SupportTicketWithMessages, SupportMessageResponse
)
from app.repositories.support_repository import SupportRepository
from app.core.dependencies import get_current_user, get_current_admin
from app.models.user import User

router = APIRouter()


@router.post("/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create support ticket"""
    support_repo = SupportRepository(session)
    
    # Create ticket
    ticket = await support_repo.create_ticket(
        user_id=current_user.id,
        subject=ticket_data.subject,
        category=ticket_data.category,
        priority=ticket_data.priority
    )
    
    # Add initial message
    await support_repo.add_message(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        sender_type="user",
        content=ticket_data.message
    )
    
    # Send ticket created email
    try:
        from app.utils.email import send_support_ticket_created_email
        from app.core.config import settings
        
        await send_support_ticket_created_email(
            user_email=current_user.email,
            username=current_user.username,
            ticket_id=str(ticket.id),
            subject=ticket_data.subject,
            priority=ticket_data.priority,
            status=ticket.status,
            ticket_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/support/{ticket.id}"
        )
    except Exception as e:
        print(f"Failed to send ticket created email: {e}")
    
    return ticket


@router.get("/tickets")
async def get_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user's tickets"""
    skip = (page - 1) * limit
    support_repo = SupportRepository(session)
    tickets = await support_repo.get_user_tickets(current_user.id, skip, limit)
    
    return {
        "tickets": tickets,
        "page": page,
        "limit": limit
    }


@router.get("/tickets/{ticket_id}", response_model=SupportTicketWithMessages)
async def get_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get ticket details with messages"""
    import json
    
    support_repo = SupportRepository(session)
    ticket = await support_repo.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if ticket.user_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this ticket"
        )
    
    messages = await support_repo.get_messages(ticket_id)
    
    # Convert attachments from JSON string to list for each message
    messages_list = []
    for msg in messages:
        msg_dict = {
            "id": msg.id,
            "ticket_id": msg.ticket_id,
            "sender_id": msg.sender_id,
            "sender_type": msg.sender_type,
            "content": msg.content,
            "created_at": msg.created_at,
            "attachments": []
        }
        
        # Parse attachments JSON string
        if hasattr(msg, 'attachments') and msg.attachments:
            if isinstance(msg.attachments, str):
                try:
                    msg_dict['attachments'] = json.loads(msg.attachments)
                except:
                    msg_dict['attachments'] = []
            elif isinstance(msg.attachments, list):
                msg_dict['attachments'] = msg.attachments
        
        messages_list.append(msg_dict)
    
    # Return ticket with messages
    ticket_dict = {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "subject": ticket.subject,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_to": ticket.assigned_to,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
        "messages": messages_list
    }
    
    return ticket_dict


@router.post("/tickets/{ticket_id}/messages")
async def send_message(
    ticket_id: UUID,
    message_data: SupportMessageCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Send message in ticket"""
    import json
    
    support_repo = SupportRepository(session)
    ticket = await support_repo.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if ticket.user_id != current_user.id and current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send messages in this ticket"
        )
    
    sender_type = "admin" if current_user.user_type == "admin" else "user"
    
    message = await support_repo.add_message(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        sender_type=sender_type,
        content=message_data.content,
        attachments=message_data.attachments
    )
    
    # Send email if agent replied to user
    if sender_type == "admin":
        try:
            from app.utils.email import send_support_ticket_reply_email
            from app.core.config import settings
            from sqlalchemy import select
            
            user_result = await session.execute(
                select(User).where(User.id == ticket.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                await send_support_ticket_reply_email(
                    user_email=user.email,
                    username=user.username,
                    ticket_id=str(ticket.id),
                    agent_name="Support Team",
                    message=message_data.content,
                    ticket_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/support/{ticket.id}"
                )
        except Exception as e:
            print(f"Failed to send ticket reply email: {e}")
    
    # Convert attachments from JSON string to list for response
    message_dict = message.model_dump() if hasattr(message, 'model_dump') else message.__dict__
    if 'attachments' in message_dict and isinstance(message_dict['attachments'], str):
        try:
            message_dict['attachments'] = json.loads(message_dict['attachments'])
        except:
            message_dict['attachments'] = []
    
    return message_dict


@router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: UUID,
    status_data: TicketStatusUpdate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update ticket status (admin only)"""
    support_repo = SupportRepository(session)
    ticket = await support_repo.update_ticket(ticket_id, status=status_data.status)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket


@router.put("/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: UUID,
    assign_data: TicketAssignUpdate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Assign ticket (admin only)"""
    support_repo = SupportRepository(session)
    ticket = await support_repo.update_ticket(ticket_id, assigned_to=assign_data.assigned_to)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket


@router.get("/admin/tickets")
async def get_all_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    category: str = Query(None),
    priority: str = Query(None),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get all tickets with filters (admin only)"""
    skip = (page - 1) * limit
    support_repo = SupportRepository(session)
    
    tickets = await support_repo.get_all_tickets(
        skip=skip,
        limit=limit,
        status=status,
        category=category,
        priority=priority
    )
    
    return {
        "tickets": tickets,
        "page": page,
        "limit": limit,
        "filters": {
            "status": status,
            "category": category,
            "priority": priority
        }
    }


@router.get("/admin/stats")
async def get_support_stats(
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Get support statistics (admin only)"""
    support_repo = SupportRepository(session)
    stats = await support_repo.get_stats()
    
    return stats



# FAQ Endpoints

@router.get("/faqs", response_model=list[FAQResponse])
async def get_faqs(
    category: str = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """Get FAQs (public endpoint)"""
    support_repo = SupportRepository(session)
    faqs = await support_repo.get_faqs(category=category)
    return faqs


@router.get("/faqs/{faq_id}", response_model=FAQResponse)
async def get_faq(
    faq_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get single FAQ and increment view count"""
    support_repo = SupportRepository(session)
    faq = await support_repo.get_faq(faq_id)
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    # Increment view count
    await support_repo.increment_faq_views(faq_id)
    
    return faq


@router.post("/faqs/{faq_id}/helpful")
async def mark_faq_helpful(
    faq_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Mark FAQ as helpful"""
    support_repo = SupportRepository(session)
    faq = await support_repo.increment_faq_helpful(faq_id)
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    return {"message": "Thank you for your feedback"}


@router.post("/admin/faqs", response_model=FAQResponse)
async def create_faq(
    faq_data: FAQCreate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Create FAQ (admin only)"""
    support_repo = SupportRepository(session)
    faq = await support_repo.create_faq(**faq_data.model_dump())
    return faq


@router.put("/admin/faqs/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: UUID,
    faq_data: FAQUpdate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Update FAQ (admin only)"""
    support_repo = SupportRepository(session)
    faq = await support_repo.update_faq(faq_id, **faq_data.model_dump(exclude_unset=True))
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    return faq


@router.delete("/admin/faqs/{faq_id}")
async def delete_faq(
    faq_id: UUID,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Delete FAQ (admin only)"""
    support_repo = SupportRepository(session)
    success = await support_repo.delete_faq(faq_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FAQ not found"
        )
    
    return {"message": "FAQ deleted successfully"}
