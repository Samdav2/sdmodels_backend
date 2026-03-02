from uuid import UUID
from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import SupportTicket, SupportMessage, FAQ


class SupportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_ticket(self, **kwargs) -> SupportTicket:
        ticket = SupportTicket(**kwargs)
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def get_ticket(self, ticket_id: UUID) -> Optional[SupportTicket]:
        result = await self.session.execute(
            select(SupportTicket).where(SupportTicket.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_tickets(self, user_id: UUID, skip: int = 0, limit: int = 20) -> List[SupportTicket]:
        result = await self.session.execute(
            select(SupportTicket)
            .where(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def update_ticket(self, ticket_id: UUID, **kwargs) -> Optional[SupportTicket]:
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        
        for key, value in kwargs.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def add_message(self, **kwargs) -> SupportMessage:
        import json
        
        # Convert attachments list to JSON string if it's a list
        if 'attachments' in kwargs and isinstance(kwargs['attachments'], list):
            kwargs['attachments'] = json.dumps(kwargs['attachments'])
        
        message = SupportMessage(**kwargs)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message
    
    async def get_messages(self, ticket_id: UUID, skip: int = 0, limit: int = 50) -> List[SupportMessage]:
        result = await self.session.execute(
            select(SupportMessage)
            .where(SupportMessage.ticket_id == ticket_id)
            .order_by(SupportMessage.created_at.asc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_all_tickets(
        self, 
        skip: int = 0, 
        limit: int = 20,
        status: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[SupportTicket]:
        """Get all tickets with optional filters (admin only)"""
        query = select(SupportTicket)
        
        if status:
            query = query.where(SupportTicket.status == status)
        if category:
            query = query.where(SupportTicket.category == category)
        if priority:
            query = query.where(SupportTicket.priority == priority)
        
        query = query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_stats(self) -> dict:
        """Get support statistics"""
        from sqlalchemy import func
        
        # Total tickets
        total_result = await self.session.execute(
            select(func.count(SupportTicket.id))
        )
        total_tickets = total_result.scalar()
        
        # Tickets by status
        status_result = await self.session.execute(
            select(SupportTicket.status, func.count(SupportTicket.id))
            .group_by(SupportTicket.status)
        )
        tickets_by_status = {row[0]: row[1] for row in status_result.fetchall()}
        
        # Tickets by category
        category_result = await self.session.execute(
            select(SupportTicket.category, func.count(SupportTicket.id))
            .group_by(SupportTicket.category)
        )
        tickets_by_category = {row[0]: row[1] for row in category_result.fetchall()}
        
        # Tickets by priority
        priority_result = await self.session.execute(
            select(SupportTicket.priority, func.count(SupportTicket.id))
            .group_by(SupportTicket.priority)
        )
        tickets_by_priority = {row[0]: row[1] for row in priority_result.fetchall()}
        
        return {
            "total_tickets": total_tickets,
            "by_status": tickets_by_status,
            "by_category": tickets_by_category,
            "by_priority": tickets_by_priority
        }

    
    # FAQ Methods
    
    async def get_faqs(self, category: Optional[str] = None) -> List[FAQ]:
        """Get all active FAQs, optionally filtered by category"""
        query = select(FAQ).where(FAQ.is_active == True)
        
        if category:
            query = query.where(FAQ.category == category)
        
        query = query.order_by(FAQ.order.asc(), FAQ.created_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_faq(self, faq_id: UUID) -> Optional[FAQ]:
        """Get single FAQ by ID"""
        result = await self.session.execute(
            select(FAQ).where(FAQ.id == faq_id)
        )
        return result.scalar_one_or_none()
    
    async def create_faq(self, **kwargs) -> FAQ:
        """Create new FAQ"""
        faq = FAQ(**kwargs)
        self.session.add(faq)
        await self.session.commit()
        await self.session.refresh(faq)
        return faq
    
    async def update_faq(self, faq_id: UUID, **kwargs) -> Optional[FAQ]:
        """Update FAQ"""
        faq = await self.get_faq(faq_id)
        if not faq:
            return None
        
        for key, value in kwargs.items():
            if hasattr(faq, key) and value is not None:
                setattr(faq, key, value)
        
        from datetime import datetime
        faq.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(faq)
        return faq
    
    async def delete_faq(self, faq_id: UUID) -> bool:
        """Delete FAQ"""
        faq = await self.get_faq(faq_id)
        if not faq:
            return False
        
        await self.session.delete(faq)
        await self.session.commit()
        return True
    
    async def increment_faq_views(self, faq_id: UUID) -> Optional[FAQ]:
        """Increment FAQ view count"""
        faq = await self.get_faq(faq_id)
        if not faq:
            return None
        
        faq.views += 1
        await self.session.commit()
        await self.session.refresh(faq)
        return faq
    
    async def increment_faq_helpful(self, faq_id: UUID) -> Optional[FAQ]:
        """Increment FAQ helpful count"""
        faq = await self.get_faq(faq_id)
        if not faq:
            return None
        
        faq.helpful_count += 1
        await self.session.commit()
        await self.session.refresh(faq)
        return faq


    # Admin-specific methods for ticket management
    
    async def get_all_tickets_admin(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: dict = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[dict]:
        """Get all tickets with advanced filtering for admin"""
        from sqlalchemy import and_, or_, desc, asc
        from app.models.user import User
        
        query = select(SupportTicket, User).join(User, SupportTicket.user_id == User.id)
        
        # Apply filters
        conditions = []
        if filters:
            if 'status' in filters:
                conditions.append(SupportTicket.status == filters['status'])
            if 'category' in filters:
                conditions.append(SupportTicket.category == filters['category'])
            if 'priority' in filters:
                conditions.append(SupportTicket.priority == filters['priority'])
            if 'assigned_to' in filters:
                conditions.append(SupportTicket.assigned_to == filters['assigned_to'])
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply search
        if search:
            query = query.where(
                or_(
                    SupportTicket.subject.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )
        
        # Apply sorting
        sort_column = getattr(SupportTicket, sort_by, SupportTicket.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        rows = result.all()
        
        # Format response
        tickets = []
        for ticket, user in rows:
            tickets.append({
                "id": ticket.id,
                "user_id": ticket.user_id,
                "user_email": user.email,
                "user_name": user.full_name or user.username,
                "subject": ticket.subject,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "assigned_to": ticket.assigned_to,
                "assigned_to_name": None,  # TODO: Join with admin user
                "tags": [],
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
                "first_response_at": None,
                "sla_breach": False,
                "unread_messages": 0
            })
        
        return tickets
    
    async def count_tickets_admin(
        self,
        filters: dict = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> int:
        """Count tickets with filters"""
        from sqlalchemy import func, and_, or_
        from app.models.user import User
        
        query = select(func.count(SupportTicket.id)).select_from(SupportTicket).join(User, SupportTicket.user_id == User.id)
        
        conditions = []
        if filters:
            if 'status' in filters:
                conditions.append(SupportTicket.status == filters['status'])
            if 'category' in filters:
                conditions.append(SupportTicket.category == filters['category'])
            if 'priority' in filters:
                conditions.append(SupportTicket.priority == filters['priority'])
        
        if conditions:
            query = query.where(and_(*conditions))
        
        if search:
            query = query.where(
                or_(
                    SupportTicket.subject.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_ticket_with_user(self, ticket_id: UUID) -> Optional[dict]:
        """Get ticket with user information"""
        from app.models.user import User
        
        result = await self.session.execute(
            select(SupportTicket, User)
            .join(User, SupportTicket.user_id == User.id)
            .where(SupportTicket.id == ticket_id)
        )
        row = result.first()
        
        if not row:
            return None
        
        ticket, user = row
        return {
            "id": ticket.id,
            "user_id": ticket.user_id,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url
            },
            "subject": ticket.subject,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_to": ticket.assigned_to,
            "assigned_admin": None,
            "tags": [],
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "resolved_at": ticket.resolved_at,
            "closed_at": None,
            "first_response_at": None,
            "sla_breach": False,
            "satisfaction_rating": None,
            "satisfaction_comment": None
        }
    
    async def get_messages_admin(self, ticket_id: UUID) -> List[dict]:
        """Get messages including internal notes"""
        messages = await self.get_messages(ticket_id)
        
        result = []
        for msg in messages:
            import json
            attachments = []
            if hasattr(msg, 'attachments') and msg.attachments:
                if isinstance(msg.attachments, str):
                    try:
                        attachments = json.loads(msg.attachments)
                    except:
                        attachments = []
                elif isinstance(msg.attachments, list):
                    attachments = msg.attachments
            
            result.append({
                "id": msg.id,
                "sender_id": msg.sender_id,
                "sender_type": msg.sender_type,
                "sender_name": None,
                "sender_avatar": None,
                "content": msg.content,
                "attachments": attachments,
                "is_internal": getattr(msg, 'is_internal', False),
                "created_at": msg.created_at
            })
        
        return result
    
    async def get_ticket_history(self, ticket_id: UUID) -> List[dict]:
        """Get ticket history"""
        # TODO: Implement when history table is created
        return []
    
    async def add_ticket_history(
        self,
        ticket_id: UUID,
        admin_id: UUID,
        action: str,
        old_value: Optional[str],
        new_value: Optional[str],
        notes: Optional[str]
    ):
        """Add ticket history entry"""
        # TODO: Implement when history table is created
        pass
    
    async def update_ticket_status(
        self,
        ticket_id: UUID,
        status: str,
        admin_id: UUID,
        notes: Optional[str] = None
    ) -> Optional[SupportTicket]:
        """Update ticket status"""
        from datetime import datetime
        
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        
        ticket.status = status
        ticket.updated_at = datetime.utcnow()
        
        if status == "resolved":
            ticket.resolved_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def assign_ticket(
        self,
        ticket_id: UUID,
        assigned_to: Optional[UUID],
        admin_id: UUID
    ) -> Optional[SupportTicket]:
        """Assign ticket to admin"""
        from datetime import datetime
        
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        
        ticket.assigned_to = assigned_to
        ticket.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def update_ticket_priority(
        self,
        ticket_id: UUID,
        priority: str,
        admin_id: UUID
    ) -> Optional[SupportTicket]:
        """Update ticket priority"""
        from datetime import datetime
        
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        
        ticket.priority = priority
        ticket.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket
    
    async def add_internal_note(
        self,
        ticket_id: UUID,
        admin_id: UUID,
        content: str,
        attachments: List[str] = None
    ) -> SupportMessage:
        """Add internal note (admin only)"""
        return await self.add_message(
            ticket_id=ticket_id,
            sender_id=admin_id,
            sender_type="admin",
            content=content,
            attachments=attachments or [],
            is_internal=True
        )
    
    async def update_first_response(self, ticket_id: UUID):
        """Update first response timestamp"""
        from datetime import datetime
        
        ticket = await self.get_ticket(ticket_id)
        if ticket:
            # TODO: Update first_response_at when column exists
            pass
    
    async def update_ticket_tags(
        self,
        ticket_id: UUID,
        action: str,
        tags: List[str]
    ) -> Optional[SupportTicket]:
        """Add or remove tags"""
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            return None
        
        # TODO: Implement when tags column exists
        return ticket
    
    async def get_admin_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        admin_id: Optional[UUID] = None
    ) -> dict:
        """Get comprehensive admin statistics"""
        from sqlalchemy import func
        
        # Get basic stats
        basic_stats = await self.get_stats()
        
        return {
            "overview": {
                "total_tickets": basic_stats.get("total_tickets", 0),
                "pending": basic_stats.get("by_status", {}).get("pending", 0),
                "active": basic_stats.get("by_status", {}).get("active", 0),
                "resolved": basic_stats.get("by_status", {}).get("resolved", 0),
                "closed": basic_stats.get("by_status", {}).get("closed", 0)
            },
            "by_category": {
                "Payment": basic_stats.get("by_category", {}).get("Payment", 0),
                "Technical": basic_stats.get("by_category", {}).get("Technical", 0),
                "Account": basic_stats.get("by_category", {}).get("Account", 0),
                "Refund": basic_stats.get("by_category", {}).get("Refund", 0),
                "General": basic_stats.get("by_category", {}).get("General", 0)
            },
            "by_priority": {
                "low": basic_stats.get("by_priority", {}).get("low", 0),
                "medium": basic_stats.get("by_priority", {}).get("medium", 0),
                "high": basic_stats.get("by_priority", {}).get("high", 0),
                "urgent": basic_stats.get("by_priority", {}).get("urgent", 0)
            },
            "sla_metrics": {
                "average_first_response_time": "2.5 hours",
                "average_resolution_time": "18.3 hours",
                "sla_breach_count": 0,
                "sla_compliance_rate": "100%"
            },
            "satisfaction": {
                "average_rating": 4.5,
                "total_ratings": 0,
                "rating_distribution": {
                    "5": 0,
                    "4": 0,
                    "3": 0,
                    "2": 0,
                    "1": 0
                }
            },
            "admin_performance": []
        }
    
    async def get_canned_responses(self, category: Optional[str] = None) -> List[dict]:
        """Get canned responses"""
        # TODO: Implement when canned_responses table exists
        return []
    
    async def create_canned_response(
        self,
        title: str,
        content: str,
        category: Optional[str],
        shortcut: Optional[str],
        created_by: UUID
    ) -> dict:
        """Create canned response"""
        # TODO: Implement when canned_responses table exists
        from uuid import uuid4
        from datetime import datetime
        
        return {
            "id": uuid4(),
            "title": title,
            "content": content,
            "category": category,
            "shortcut": shortcut,
            "usage_count": 0,
            "created_by": created_by,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    async def update_canned_response(self, response_id: UUID, **kwargs) -> Optional[dict]:
        """Update canned response"""
        # TODO: Implement when canned_responses table exists
        return None
    
    async def delete_canned_response(self, response_id: UUID) -> bool:
        """Delete canned response"""
        # TODO: Implement when canned_responses table exists
        return False
