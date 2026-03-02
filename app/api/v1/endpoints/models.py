from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse, ModelListResponse, ModelCommentCreate
from app.services.model_service import ModelService
from app.core.dependencies import get_current_user, get_current_creator, get_optional_user
from app.models.user import User

router = APIRouter()


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    model_data: ModelCreate,
    current_user: User = Depends(get_current_creator),
    session: AsyncSession = Depends(get_session)
):
    """Upload new 3D model"""
    model_service = ModelService(session)
    return await model_service.create_model(current_user.id, model_data)


@router.get("/my-models", response_model=ModelListResponse)
async def get_my_models(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("newest", regex="^(newest|popular|price_low|price_high)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get models created/uploaded by the current user
    Returns only models where creator_id matches the authenticated user
    """
    from sqlalchemy import select, func, or_
    from app.models.model import Model
    
    skip = (page - 1) * limit
    
    # Base query - only models created by current user
    query = select(Model).where(Model.creator_id == current_user.id)
    
    # Apply filters
    if category:
        query = query.where(Model.category == category)
    
    if status:
        query = query.where(Model.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Model.title.ilike(search_term),
                Model.description.ilike(search_term),
                Model.tags.contains([search.lower()])
            )
        )
    
    # Apply sorting
    if sort == "newest":
        query = query.order_by(Model.created_at.desc())
    elif sort == "popular":
        query = query.order_by(Model.downloads.desc())
    elif sort == "price_low":
        query = query.order_by(Model.price.asc())
    elif sort == "price_high":
        query = query.order_by(Model.price.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(Model).where(
        Model.creator_id == current_user.id
    )
    
    if category:
        count_query = count_query.where(Model.category == category)
    if status:
        count_query = count_query.where(Model.status == status)
    if search:
        search_term = f"%{search}%"
        count_query = count_query.where(
            or_(
                Model.title.ilike(search_term),
                Model.description.ilike(search_term),
                Model.tags.contains([search.lower()])
            )
        )
    
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    
    # Get paginated results
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    models = result.scalars().all()
    
    return {
        "models": [ModelResponse.model_validate(model) for model in models],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/inventory", response_model=ModelListResponse)
async def get_user_inventory(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("newest", regex="^(newest|purchased|price_low|price_high)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get user's inventory - models they have purchased
    Returns complete model details with purchase information
    """
    from sqlalchemy import select, func, or_
    from app.models.model import Model
    from app.models.transaction import Purchase
    
    skip = (page - 1) * limit
    
    # Base query - join Purchase with Model to get user's purchased models
    query = select(Model).join(Purchase, Purchase.model_id == Model.id).where(
        Purchase.user_id == current_user.id
    )
    
    # Apply filters
    if category:
        query = query.where(Model.category == category)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Model.title.ilike(search_term),
                Model.description.ilike(search_term),
                Model.tags.contains([search.lower()])
            )
        )
    
    # Apply sorting
    if sort == "newest":
        query = query.order_by(Model.created_at.desc())
    elif sort == "purchased":
        query = query.order_by(Purchase.created_at.desc())
    elif sort == "price_low":
        query = query.order_by(Model.price.asc())
    elif sort == "price_high":
        query = query.order_by(Model.price.desc())
    elif sort == "popular":
        query = query.order_by(Model.downloads.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(Model).join(
        Purchase, Purchase.model_id == Model.id
    ).where(Purchase.user_id == current_user.id)
    
    if category:
        count_query = count_query.where(Model.category == category)
    if search:
        search_term = f"%{search}%"
        count_query = count_query.where(
            or_(
                Model.title.ilike(search_term),
                Model.description.ilike(search_term),
                Model.tags.contains([search.lower()])
            )
        )
    
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    
    # Get paginated results
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    models = result.scalars().all()
    
    return {
        "models": [ModelResponse.model_validate(model) for model in models],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("", response_model=ModelListResponse)
async def get_models(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_free: Optional[bool] = None,
    search: Optional[str] = None,
    sort: str = Query("newest", regex="^(newest|popular|price_low|price_high)$"),
    session: AsyncSession = Depends(get_session)
):
    """Get public models list with filters (marketplace)"""
    model_service = ModelService(session)
    return await model_service.get_models(
        page=page,
        limit=limit,
        category=category,
        min_price=min_price,
        max_price=max_price,
        is_free=is_free,
        search=search,
        sort=sort
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    """Get model details"""
    model_service = ModelService(session)
    return await model_service.get_model(model_id)


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    model_data: ModelUpdate,
    current_user: User = Depends(get_current_creator),
    session: AsyncSession = Depends(get_session)
):
    """Update model (creator only)"""
    model_service = ModelService(session)
    return await model_service.update_model(model_id, current_user.id, model_data)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: UUID,
    current_user: User = Depends(get_current_creator),
    session: AsyncSession = Depends(get_session)
):
    """Delete model (creator only)"""
    model_service = ModelService(session)
    await model_service.delete_model(model_id, current_user.id)
    return None


@router.post("/{model_id}/like")
async def like_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Like a model"""
    model_service = ModelService(session)
    await model_service.like_model(current_user.id, model_id)
    return {"message": "Model liked successfully"}


@router.delete("/{model_id}/like")
async def unlike_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Unlike a model"""
    model_service = ModelService(session)
    await model_service.unlike_model(current_user.id, model_id)
    return {"message": "Model unliked successfully"}


@router.post("/{model_id}/comments")
async def add_comment(
    model_id: UUID,
    comment_data: ModelCommentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Add comment to model"""
    model_service = ModelService(session)
    comment = await model_service.add_comment(
        current_user.id,
        model_id,
        comment_data.content,
        comment_data.parent_id
    )
    return comment


@router.get("/{model_id}/comments")
async def get_comments(
    model_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
):
    """Get model comments"""
    model_service = ModelService(session)
    comments = await model_service.get_comments(model_id, page, limit)
    return {"comments": comments, "page": page, "limit": limit}


@router.post("/{model_id}/view")
async def increment_view(
    model_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Increment view count"""
    model_service = ModelService(session)
    await model_service.increment_view(model_id)
    return {"message": "View counted"}
