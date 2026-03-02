from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.community import (
    CommunityCreate, CommunityUpdate, CommunityResponse, CommunityListResponse,
    CommunityDetailResponse, PostCreate, PostUpdate, PostResponse, 
    PostReactionCreate, PostCommentCreate, ReportCreate
)
from app.services.community_service import CommunityService
from app.core.dependencies import get_current_user, get_optional_user
from app.models.user import User

router = APIRouter()


@router.post("", response_model=CommunityResponse, status_code=status.HTTP_201_CREATED)
async def create_community(
    community_data: CommunityCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create new community"""
    community_service = CommunityService(session)
    return await community_service.create_community(current_user.id, community_data)


@router.get("", response_model=CommunityListResponse)
async def get_communities(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,  # None = all statuses, or specify: active, pending, suspended
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get all communities.
    If authenticated, includes is_member and user_role fields for each community.
    """
    community_service = CommunityService(session)
    user_id = current_user.id if current_user else None
    return await community_service.get_communities(page, limit, category, search, status, user_id)


@router.get("/{community_id}", response_model=CommunityDetailResponse)
async def get_community(
    community_id: UUID,
    include_members: bool = Query(True, description="Include top members"),
    include_posts: bool = Query(True, description="Include recent posts"),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get community details with optional members and posts.
    Authentication is optional - provides membership info if authenticated.
    """
    community_service = CommunityService(session)
    user_id = current_user.id if current_user else None
    return await community_service.get_community_detail(
        community_id, 
        user_id,
        include_members=include_members,
        include_posts=include_posts
    )


@router.put("/{community_id}", response_model=CommunityResponse)
async def update_community(
    community_id: UUID,
    community_data: CommunityUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update community (admin/moderator only)"""
    community_service = CommunityService(session)
    return await community_service.update_community(community_id, current_user.id, community_data)


@router.delete("/{community_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community(
    community_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete community (admin only)"""
    community_service = CommunityService(session)
    await community_service.delete_community(community_id, current_user.id)
    return None


@router.post("/{community_id}/join")
async def join_community(
    community_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Join community"""
    community_service = CommunityService(session)
    await community_service.join_community(current_user.id, community_id)
    return {"message": "Joined community successfully"}


@router.delete("/{community_id}/leave")
async def leave_community(
    community_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Leave community"""
    community_service = CommunityService(session)
    await community_service.leave_community(current_user.id, community_id)
    return {"message": "Left community successfully"}


@router.get("/{community_id}/members")
async def get_members(
    community_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """Get community members"""
    community_service = CommunityService(session)
    members = await community_service.get_members(community_id, page, limit)
    return {"members": members, "page": page, "limit": limit}


@router.post("/{community_id}/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    community_id: UUID,
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create post in community"""
    community_service = CommunityService(session)
    return await community_service.create_post(
        current_user.id,
        community_id,
        post_data.content,
        post_data.image_url,
        post_data.model_url
    )


@router.get("/{community_id}/posts")
async def get_posts(
    community_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    filter: str = Query("recent", regex="^(recent|popular|media)$"),
    session: AsyncSession = Depends(get_session)
):
    """Get community posts"""
    community_service = CommunityService(session)
    posts = await community_service.get_posts(community_id, page, limit, filter)
    return {"posts": posts, "page": page, "limit": limit}


@router.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update post (author only)"""
    community_service = CommunityService(session)
    return await community_service.update_post(post_id, current_user.id, post_data.content)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete post (author/moderator only)"""
    community_service = CommunityService(session)
    await community_service.delete_post(post_id, current_user.id)
    return None


@router.post("/posts/{post_id}/react")
async def react_to_post(
    post_id: UUID,
    reaction_data: PostReactionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """React to post"""
    community_service = CommunityService(session)
    await community_service.react_to_post(current_user.id, post_id, reaction_data.reaction_type)
    return {"message": "Reaction added successfully"}


@router.delete("/posts/{post_id}/react")
async def remove_reaction(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Remove reaction"""
    community_service = CommunityService(session)
    await community_service.remove_reaction(current_user.id, post_id)
    return {"message": "Reaction removed successfully"}


@router.post("/posts/{post_id}/comments")
async def add_comment(
    post_id: UUID,
    comment_data: PostCommentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Comment on post"""
    community_service = CommunityService(session)
    comment = await community_service.add_comment(
        current_user.id,
        post_id,
        comment_data.content,
        comment_data.parent_id
    )
    return comment


@router.get("/posts/{post_id}/comments")
async def get_comments(
    post_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get post comments with nested replies and like status if authenticated"""
    community_service = CommunityService(session)
    user_id = current_user.id if current_user else None
    return await community_service.get_comments(post_id, page, limit, user_id)


@router.post("/comments/{comment_id}/like")
async def like_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Like a comment (requires authentication)"""
    community_service = CommunityService(session)
    return await community_service.like_comment(current_user.id, comment_id)


@router.delete("/comments/{comment_id}/like")
async def unlike_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Unlike a comment (requires authentication)"""
    community_service = CommunityService(session)
    return await community_service.unlike_comment(current_user.id, comment_id)


@router.post("/posts/{post_id}/share")
async def share_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Share post"""
    # TODO: Implement share logic
    return {"message": "Post shared successfully"}


@router.post("/posts/{post_id}/report")
async def report_post(
    post_id: UUID,
    report_data: ReportCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Report post"""
    # TODO: Implement report logic
    return {"message": "Post reported successfully"}
