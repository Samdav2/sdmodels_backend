from uuid import UUID
from typing import Optional, List, Tuple
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_
import json

from app.models.community import Community, CommunityMember, CommunityPost, PostReaction, PostComment, CommentLike


class CommunityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, **kwargs) -> Community:
        # Convert rules list to JSON string
        if 'rules' in kwargs and isinstance(kwargs['rules'], list):
            kwargs['rules'] = json.dumps(kwargs['rules'])
        
        community = Community(**kwargs)
        self.session.add(community)
        await self.session.commit()
        await self.session.refresh(community)
        return community
    
    async def get_by_id(self, community_id: UUID) -> Optional[Community]:
        result = await self.session.execute(
            select(Community).where(Community.id == community_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Community]:
        result = await self.session.execute(
            select(Community).where(Community.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_membership(self, user_id: UUID, community_id: UUID) -> Optional[CommunityMember]:
        """Get user's membership in a community"""
        result = await self.session.execute(
            select(CommunityMember).where(
                and_(
                    CommunityMember.user_id == user_id,
                    CommunityMember.community_id == community_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None  # For checking membership
    ) -> Tuple[List[dict], int]:
        """
        Get all communities with optional membership info.
        Returns list of dicts with community data + is_member and user_role fields.
        """
        # Base query
        query = select(Community)
        
        # Only filter by status if specified
        if status:
            query = query.where(Community.status == status)
        
        if category:
            query = query.where(Community.category == category)
        
        if search:
            query = query.where(
                (Community.name.ilike(f"%{search}%")) | 
                (Community.description.ilike(f"%{search}%"))
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.order_by(Community.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        communities = result.scalars().all()
        
        # If user_id provided, fetch membership info in one query
        community_data = []
        if user_id and communities:
            community_ids = [c.id for c in communities]
            
            # Fetch all memberships for this user in one query
            membership_query = select(CommunityMember).where(
                and_(
                    CommunityMember.user_id == user_id,
                    CommunityMember.community_id.in_(community_ids)
                )
            )
            membership_result = await self.session.execute(membership_query)
            memberships = membership_result.scalars().all()
            
            # Create lookup dict for O(1) access
            membership_map = {m.community_id: m.role for m in memberships}
            
            # Build response with membership info
            for community in communities:
                comm_dict = {
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
                    "is_member": community.id in membership_map,
                    "user_role": membership_map.get(community.id)
                }
                community_data.append(comm_dict)
        else:
            # No user_id, return communities without membership info
            for community in communities:
                comm_dict = {
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
                    "is_member": False,
                    "user_role": None
                }
                community_data.append(comm_dict)
        
        return community_data, total
    
    async def update(self, community_id: UUID, **kwargs) -> Optional[Community]:
        community = await self.get_by_id(community_id)
        if not community:
            return None
        
        # Convert rules list to JSON string
        if 'rules' in kwargs and isinstance(kwargs['rules'], list):
            kwargs['rules'] = json.dumps(kwargs['rules'])
        
        for key, value in kwargs.items():
            if hasattr(community, key):
                setattr(community, key, value)
        
        await self.session.commit()
        await self.session.refresh(community)
        return community
    
    async def delete(self, community_id: UUID) -> bool:
        community = await self.get_by_id(community_id)
        if not community:
            return False
        
        await self.session.delete(community)
        await self.session.commit()
        return True
    
    async def join_community(self, user_id: UUID, community_id: UUID, role: str = "member") -> CommunityMember:
        # Check if already a member
        result = await self.session.execute(
            select(CommunityMember).where(
                CommunityMember.user_id == user_id,
                CommunityMember.community_id == community_id
            )
        )
        existing_member = result.scalar_one_or_none()
        
        if existing_member:
            # Already a member, just return
            return existing_member
        
        # Create new member
        member = CommunityMember(
            user_id=user_id,
            community_id=community_id,
            role=role
        )
        self.session.add(member)
        
        # Increment member count
        community = await self.get_by_id(community_id)
        if community:
            community.member_count += 1
        
        await self.session.commit()
        await self.session.refresh(member)
        return member
    
    async def leave_community(self, user_id: UUID, community_id: UUID) -> bool:
        result = await self.session.execute(
            select(CommunityMember).where(
                CommunityMember.user_id == user_id,
                CommunityMember.community_id == community_id
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            return False
        
        await self.session.delete(member)
        
        # Decrement member count
        community = await self.get_by_id(community_id)
        if community and community.member_count > 0:
            community.member_count -= 1
        
        await self.session.commit()
        return True
    
    async def get_members(self, community_id: UUID, skip: int = 0, limit: int = 50) -> List[CommunityMember]:
        result = await self.session.execute(
            select(CommunityMember)
            .where(CommunityMember.community_id == community_id)
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_top_members(self, community_id: UUID, limit: int = 5) -> List[dict]:
        """Get top members with user info"""
        from app.models.user import User
        
        # Join with users table to get user info
        query = select(
            CommunityMember.id,
            CommunityMember.user_id,
            CommunityMember.role,
            CommunityMember.joined_at,
            User.username,
            User.avatar_url
        ).join(
            User, CommunityMember.user_id == User.id
        ).where(
            CommunityMember.community_id == community_id
        ).order_by(
            # Admins first, then moderators, then by join date
            CommunityMember.role.desc(),
            CommunityMember.joined_at.asc()
        ).limit(limit)
        
        result = await self.session.execute(query)
        rows = result.fetchall()
        
        members = []
        for row in rows:
            members.append({
                "id": row[0],
                "user_id": row[1],
                "role": row[2],
                "joined_at": row[3],
                "username": row[4],
                "avatar": row[5] or "👤"  # Default avatar if none
            })
        
        return members
    
    async def create_post(self, **kwargs) -> CommunityPost:
        post = CommunityPost(**kwargs)
        self.session.add(post)
        
        # Increment post count
        community = await self.get_by_id(kwargs.get('community_id'))
        if community:
            community.post_count += 1
        
        await self.session.commit()
        await self.session.refresh(post)
        return post
    
    async def get_post(self, post_id: UUID) -> Optional[dict]:
        """Get single post with expanded model and user data"""
        from app.models.model import Model
        from app.models.user import User
        
        query = select(
            CommunityPost,
            User.username,
            User.avatar_url,
            Model.id.label('model_id'),
            Model.title.label('model_title'),
            Model.file_url.label('model_file_url'),
            Model.thumbnail_url.label('model_thumbnail_url'),
            Model.file_formats.label('model_file_formats'),
            Model.category.label('model_category'),
            Model.poly_count.label('model_poly_count')
        ).join(
            User, CommunityPost.author_id == User.id
        ).outerjoin(
            Model, CommunityPost.model_url == Model.file_url
        ).where(
            CommunityPost.id == post_id
        )
        
        result = await self.session.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        post = row[0]  # CommunityPost object
        post_dict = {
            "id": post.id,
            "community_id": post.community_id,
            "author_id": post.author_id,
            "author_username": row[1],  # username
            "author_avatar": row[2] or "👤",  # avatar_url
            "content": post.content,
            "image_url": post.image_url,
            "model_url": post.model_url,
            "reactions": post.reactions,
            "comment_count": post.comment_count,
            "share_count": post.share_count,
            "is_pinned": post.is_pinned,
            "created_at": post.created_at,
            "updated_at": post.updated_at
        }
        
        # Add expanded model data if model exists
        if row[3]:  # model_id exists
            # Parse file_formats from JSON string to list
            file_formats = []
            if row[7]:  # model_file_formats
                try:
                    file_formats = json.loads(row[7])
                except json.JSONDecodeError:
                    file_formats = []
            
            post_dict["model"] = {
                "id": row[3],  # model_id
                "title": row[4],  # model_title
                "file_url": row[5],  # model_file_url
                "thumbnail_url": row[6],  # model_thumbnail_url
                "file_formats": file_formats,  # parsed list
                "category": row[8],  # model_category
                "poly_count": row[9]  # model_poly_count
            }
        else:
            post_dict["model"] = None
        
        return post_dict
    
    async def get_posts(
        self,
        community_id: UUID,
        skip: int = 0,
        limit: int = 20,
        filter_type: str = "recent"
    ) -> List[dict]:
        """Get posts with expanded model data"""
        from app.models.model import Model
        from app.models.user import User
        
        # Query posts with user info
        query = select(
            CommunityPost,
            User.username,
            User.avatar_url,
            Model.id.label('model_id'),
            Model.title.label('model_title'),
            Model.file_url.label('model_file_url'),
            Model.thumbnail_url.label('model_thumbnail_url'),
            Model.file_formats.label('model_file_formats'),
            Model.category.label('model_category'),
            Model.poly_count.label('model_poly_count')
        ).join(
            User, CommunityPost.author_id == User.id
        ).outerjoin(
            Model, CommunityPost.model_url == Model.file_url
        ).where(
            CommunityPost.community_id == community_id,
            CommunityPost.is_deleted == False
        )
        
        if filter_type == "popular":
            query = query.order_by(CommunityPost.comment_count.desc())
        else:  # recent
            query = query.order_by(CommunityPost.created_at.desc())
        
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        rows = result.fetchall()
        
        # Build post dictionaries with expanded data
        posts = []
        for row in rows:
            post = row[0]  # CommunityPost object
            post_dict = {
                "id": post.id,
                "community_id": post.community_id,
                "author_id": post.author_id,
                "author_username": row[1],  # username
                "author_avatar": row[2] or "👤",  # avatar_url
                "content": post.content,
                "image_url": post.image_url,
                "model_url": post.model_url,
                "reactions": post.reactions,
                "comment_count": post.comment_count,
                "share_count": post.share_count,
                "is_pinned": post.is_pinned,
                "created_at": post.created_at,
                "updated_at": post.updated_at
            }
            
            # Add expanded model data if model exists
            if row[3]:  # model_id exists
                # Parse file_formats from JSON string to list
                file_formats = []
                if row[7]:  # model_file_formats
                    try:
                        file_formats = json.loads(row[7])
                    except json.JSONDecodeError:
                        file_formats = []
                
                post_dict["model"] = {
                    "id": row[3],  # model_id
                    "title": row[4],  # model_title
                    "file_url": row[5],  # model_file_url
                    "thumbnail_url": row[6],  # model_thumbnail_url
                    "file_formats": file_formats,  # parsed list
                    "category": row[8],  # model_category
                    "poly_count": row[9]  # model_poly_count
                }
            else:
                post_dict["model"] = None
            
            posts.append(post_dict)
        
        return posts
    
    async def update_post(self, post_id: UUID, **kwargs) -> Optional[dict]:
        # Get raw post object for update
        result = await self.session.execute(
            select(CommunityPost).where(CommunityPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            return None
        
        for key, value in kwargs.items():
            if hasattr(post, key):
                setattr(post, key, value)
        
        await self.session.commit()
        await self.session.refresh(post)
        
        # Return expanded post data
        return await self.get_post(post_id)
    
    async def delete_post(self, post_id: UUID) -> bool:
        # Get raw post object for deletion
        result = await self.session.execute(
            select(CommunityPost).where(CommunityPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            return False
        
        post.is_deleted = True
        await self.session.commit()
        return True
    
    async def react_to_post(self, user_id: UUID, post_id: UUID, reaction_type: str) -> PostReaction:
        # Check if reaction already exists
        result = await self.session.execute(
            select(PostReaction).where(
                PostReaction.user_id == user_id,
                PostReaction.post_id == post_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update reaction type
            existing.reaction_type = reaction_type
            await self.session.commit()
            return existing
        
        # Create new reaction
        reaction = PostReaction(user_id=user_id, post_id=post_id, reaction_type=reaction_type)
        self.session.add(reaction)
        
        # Update post reactions count - get raw post object
        post_result = await self.session.execute(
            select(CommunityPost).where(CommunityPost.id == post_id)
        )
        post = post_result.scalar_one_or_none()
        
        if post:
            reactions = json.loads(post.reactions)
            reactions[reaction_type] = reactions.get(reaction_type, 0) + 1
            post.reactions = json.dumps(reactions)
        
        await self.session.commit()
        await self.session.refresh(reaction)
        return reaction
    
    async def remove_reaction(self, user_id: UUID, post_id: UUID) -> bool:
        result = await self.session.execute(
            select(PostReaction).where(
                PostReaction.user_id == user_id,
                PostReaction.post_id == post_id
            )
        )
        reaction = result.scalar_one_or_none()
        
        if not reaction:
            return False
        
        # Update post reactions count - get raw post object
        post_result = await self.session.execute(
            select(CommunityPost).where(CommunityPost.id == post_id)
        )
        post = post_result.scalar_one_or_none()
        
        if post:
            reactions = json.loads(post.reactions)
            if reaction.reaction_type in reactions and reactions[reaction.reaction_type] > 0:
                reactions[reaction.reaction_type] -= 1
            post.reactions = json.dumps(reactions)
        
        await self.session.delete(reaction)
        await self.session.commit()
        return True
    
    async def add_comment(self, author_id: UUID, post_id: UUID, content: str, parent_id: Optional[UUID] = None) -> PostComment:
        comment = PostComment(
            author_id=author_id,
            post_id=post_id,
            content=content,
            parent_id=parent_id
        )
        self.session.add(comment)
        
        # Increment comment count - get raw post object
        post_result = await self.session.execute(
            select(CommunityPost).where(CommunityPost.id == post_id)
        )
        post = post_result.scalar_one_or_none()
        
        if post:
            post.comment_count += 1
        
        await self.session.commit()
        await self.session.refresh(comment)
        return comment
    
    async def get_comments(self, post_id: UUID, skip: int = 0, limit: int = 50, user_id: Optional[UUID] = None) -> dict:
        """Get comments with user information, like status, and nested replies"""
        from app.models.user import User
        
        # Get ALL comments for this post (not paginated for proper nesting)
        # We'll apply pagination to top-level comments only
        query = select(
            PostComment.id,
            PostComment.post_id,
            PostComment.author_id,
            PostComment.content,
            PostComment.parent_id,
            PostComment.likes,
            PostComment.created_at,
            User.username,
            User.avatar_url
        ).join(
            User, PostComment.author_id == User.id
        ).where(
            PostComment.post_id == post_id
        ).order_by(
            PostComment.created_at.asc()  # Oldest first for proper threading
        )
        
        result = await self.session.execute(query)
        rows = result.fetchall()
        
        # Build comment dictionary
        all_comments = {}
        comment_ids = []
        
        for row in rows:
            comment_id = row[0]
            comment_ids.append(comment_id)
            all_comments[comment_id] = {
                "id": comment_id,
                "post_id": row[1],
                "author_id": row[2],
                "content": row[3],
                "parent_id": row[4],
                "likes": row[5],
                "created_at": row[6],
                "author_username": row[7],
                "author_avatar": row[8] or "👤",
                "user_has_liked": False,
                "replies": []  # Will hold nested replies
            }
        
        # Get like status if user_id provided
        if user_id and comment_ids:
            like_status = await self.get_comment_like_status(user_id, comment_ids)
            for comment_id in all_comments:
                all_comments[comment_id]["user_has_liked"] = like_status.get(comment_id, False)
        
        # Build nested structure
        top_level_comments = []
        
        for comment_id, comment in all_comments.items():
            if comment["parent_id"] is None:
                # Top-level comment
                top_level_comments.append(comment)
            else:
                # Reply - add to parent's replies
                parent_id = comment["parent_id"]
                if parent_id in all_comments:
                    all_comments[parent_id]["replies"].append(comment)
        
        # Sort top-level comments by created_at descending (newest first)
        top_level_comments.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination to top-level comments only
        total_top_level = len(top_level_comments)
        paginated_comments = top_level_comments[skip:skip + limit]
        
        return {
            "comments": paginated_comments,
            "total": total_top_level,
            "total_with_replies": len(all_comments)
        }

    
    async def like_comment(self, user_id: UUID, comment_id: UUID) -> bool:
        """Like a comment"""
        # Check if already liked
        result = await self.session.execute(
            select(CommentLike).where(
                CommentLike.user_id == user_id,
                CommentLike.comment_id == comment_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return False  # Already liked
        
        # Create like
        like = CommentLike(user_id=user_id, comment_id=comment_id)
        self.session.add(like)
        
        # Increment comment likes count
        comment_result = await self.session.execute(
            select(PostComment).where(PostComment.id == comment_id)
        )
        comment = comment_result.scalar_one_or_none()
        
        if comment:
            comment.likes += 1
        
        await self.session.commit()
        return True
    
    async def unlike_comment(self, user_id: UUID, comment_id: UUID) -> bool:
        """Unlike a comment"""
        result = await self.session.execute(
            select(CommentLike).where(
                CommentLike.user_id == user_id,
                CommentLike.comment_id == comment_id
            )
        )
        like = result.scalar_one_or_none()
        
        if not like:
            return False  # Not liked
        
        # Remove like
        await self.session.delete(like)
        
        # Decrement comment likes count
        comment_result = await self.session.execute(
            select(PostComment).where(PostComment.id == comment_id)
        )
        comment = comment_result.scalar_one_or_none()
        
        if comment and comment.likes > 0:
            comment.likes -= 1
        
        await self.session.commit()
        return True
    
    async def get_comment_like_status(self, user_id: UUID, comment_ids: List[UUID]) -> dict:
        """Get like status for multiple comments"""
        if not comment_ids:
            return {}
        
        result = await self.session.execute(
            select(CommentLike.comment_id).where(
                and_(
                    CommentLike.user_id == user_id,
                    CommentLike.comment_id.in_(comment_ids)
                )
            )
        )
        
        liked_comment_ids = {row[0] for row in result.fetchall()}
        return {comment_id: comment_id in liked_comment_ids for comment_id in comment_ids}
