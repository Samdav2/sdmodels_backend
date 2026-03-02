from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.repositories.community_repository import CommunityRepository
from app.schemas.community import CommunityCreate, CommunityUpdate


class CommunityService:
    def __init__(self, session: AsyncSession):
        self.community_repo = CommunityRepository(session)
    
    async def create_community(self, creator_id: UUID, community_data: CommunityCreate):
        # Check if community name already exists
        existing = await self.community_repo.get_by_name(community_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Community with name '{community_data.name}' already exists"
            )
        
        try:
            # Create the community
            community = await self.community_repo.create(
                creator_id=creator_id,
                **community_data.model_dump()
            )
            
            # Automatically add creator as admin member
            await self.community_repo.join_community(
                user_id=creator_id,
                community_id=community.id,
                role="admin"
            )
            
            return community
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create community. Name may already exist."
            )
    
    async def get_community(self, community_id: UUID, user_id: Optional[UUID] = None):
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community not found"
            )
        
        # Check membership if user_id provided
        is_member = False
        user_role = None
        
        if user_id:
            membership = await self.community_repo.get_membership(user_id, community_id)
            if membership:
                is_member = True
                user_role = membership.role
        
        # Convert to dict and add membership info
        community_dict = {
            "id": community.id,
            "name": community.name,
            "description": community.description,
            "icon": community.icon,
            "banner_gradient": community.banner_gradient,
            "category": community.category,
            "creator_id": community.creator_id,
            "member_count": community.member_count,
            "post_count": community.post_count,
            "status": community.status,
            "is_private": community.is_private,
            "require_approval": community.require_approval,
            "rules": community.rules,
            "created_at": community.created_at,
            "updated_at": community.updated_at,
            "is_member": is_member,
            "user_role": user_role
        }
        
        return community_dict
    
    async def get_community_detail(
        self, 
        community_id: UUID, 
        user_id: Optional[UUID] = None,
        include_members: bool = True,
        include_posts: bool = True
    ):
        """Get community with detailed info including members and posts"""
        # Get basic community info
        community_dict = await self.get_community(community_id, user_id)
        
        # Add top members if requested
        if include_members:
            top_members = await self.community_repo.get_top_members(community_id, limit=5)
            community_dict["top_members"] = top_members
        else:
            community_dict["top_members"] = []
        
        # Add recent posts if requested
        if include_posts:
            recent_posts = await self.community_repo.get_posts(community_id, skip=0, limit=5, filter_type="recent")
            community_dict["recent_posts"] = recent_posts
        else:
            community_dict["recent_posts"] = []
        
        return community_dict
    
    async def get_communities(
        self,
        page: int = 1,
        limit: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None  # For checking membership
    ):
        skip = (page - 1) * limit
        communities, total = await self.community_repo.get_all(
            skip=skip,
            limit=limit,
            category=category,
            search=search,
            status=status,
            user_id=user_id
        )
        
        return {
            "communities": communities,
            "total": total,
            "page": page,
            "limit": limit
        }
    
    async def update_community(self, community_id: UUID, user_id: UUID, community_data: CommunityUpdate):
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community not found"
            )
        
        if community.creator_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this community"
            )
        
        return await self.community_repo.update(
            community_id,
            **community_data.model_dump(exclude_unset=True)
        )
    
    async def delete_community(self, community_id: UUID, user_id: UUID):
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community not found"
            )
        
        if community.creator_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this community"
            )
        
        return await self.community_repo.delete(community_id)
    
    async def join_community(self, user_id: UUID, community_id: UUID):
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community not found"
            )
        
        return await self.community_repo.join_community(user_id, community_id)
    
    async def leave_community(self, user_id: UUID, community_id: UUID):
        return await self.community_repo.leave_community(user_id, community_id)
    
    async def get_members(self, community_id: UUID, page: int = 1, limit: int = 50):
        skip = (page - 1) * limit
        return await self.community_repo.get_members(community_id, skip, limit)
    
    async def create_post(self, author_id: UUID, community_id: UUID, content: str, image_url: Optional[str] = None, model_url: Optional[str] = None):
        community = await self.community_repo.get_by_id(community_id)
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community not found"
            )
        
        return await self.community_repo.create_post(
            author_id=author_id,
            community_id=community_id,
            content=content,
            image_url=image_url,
            model_url=model_url
        )
    
    async def get_posts(self, community_id: UUID, page: int = 1, limit: int = 20, filter_type: str = "recent"):
        skip = (page - 1) * limit
        return await self.community_repo.get_posts(community_id, skip, limit, filter_type)
    
    async def update_post(self, post_id: UUID, author_id: UUID, content: str):
        post = await self.community_repo.get_post(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if post["author_id"] != author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this post"
            )
        
        return await self.community_repo.update_post(post_id, content=content)
    
    async def delete_post(self, post_id: UUID, author_id: UUID):
        post = await self.community_repo.get_post(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if post["author_id"] != author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this post"
            )
        
        return await self.community_repo.delete_post(post_id)
    
    async def react_to_post(self, user_id: UUID, post_id: UUID, reaction_type: str):
        post = await self.community_repo.get_post(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        return await self.community_repo.react_to_post(user_id, post_id, reaction_type)
    
    async def remove_reaction(self, user_id: UUID, post_id: UUID):
        return await self.community_repo.remove_reaction(user_id, post_id)
    
    async def add_comment(self, author_id: UUID, post_id: UUID, content: str, parent_id: Optional[UUID] = None):
        post = await self.community_repo.get_post(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        return await self.community_repo.add_comment(author_id, post_id, content, parent_id)
    
    async def get_comments(self, post_id: UUID, page: int = 1, limit: int = 50, user_id: Optional[UUID] = None):
        skip = (page - 1) * limit
        result = await self.community_repo.get_comments(post_id, skip, limit, user_id)
        return {
            "comments": result["comments"],
            "total": result["total"],
            "total_with_replies": result["total_with_replies"],
            "page": page,
            "limit": limit
        }
    
    async def like_comment(self, user_id: UUID, comment_id: UUID):
        success = await self.community_repo.like_comment(user_id, comment_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment already liked"
            )
        return {"message": "Comment liked successfully"}
    
    async def unlike_comment(self, user_id: UUID, comment_id: UUID):
        success = await self.community_repo.unlike_comment(user_id, comment_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment not liked"
            )
        return {"message": "Comment unliked successfully"}

    
    async def invite_to_community(
        self,
        community_id: UUID,
        inviter_id: UUID,
        invitee_email: str
    ) -> dict:
        """Invite user to community"""
        from app.utils.email import send_community_invite_email
        from app.core.config import settings
        from sqlalchemy import select
        from app.models.user import User
        
        # Get community
        community_dict = await self.get_community(community_id)
        
        # Get inviter info
        inviter_result = await self.community_repo.db.execute(
            select(User).where(User.id == inviter_id)
        )
        inviter = inviter_result.scalar_one_or_none()
        
        # Get invitee info
        invitee_result = await self.community_repo.db.execute(
            select(User).where(User.email == invitee_email)
        )
        invitee = invitee_result.scalar_one_or_none()
        
        if not invitee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email not found"
            )
        
        # Check if already a member
        membership = await self.community_repo.get_membership(invitee.id, community_id)
        if membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this community"
            )
        
        # Send invite email
        try:
            await send_community_invite_email(
                user_email=invitee.email,
                username=invitee.username,
                inviter_username=inviter.username if inviter else "Someone",
                community_name=community_dict["name"],
                community_description=community_dict["description"],
                member_count=community_dict["member_count"],
                community_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/communities/{community_id}"
            )
        except Exception as e:
            print(f"Failed to send community invite email: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send invite email"
            )
        
        return {
            "message": f"Invitation sent to {invitee_email}",
            "invitee": {
                "email": invitee.email,
                "username": invitee.username
            }
        }
