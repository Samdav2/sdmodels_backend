from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter()


@router.get("/homepage")
async def get_homepage_stats(session: AsyncSession = Depends(get_session)):
    """Get homepage statistics and featured content"""
    from sqlalchemy import select, func
    from app.models.model import Model
    from app.models.user import User
    from app.schemas.model import ModelResponse
    from app.schemas.user import UserResponse
    
    # Get platform stats
    total_models_result = await session.execute(select(func.count()).select_from(Model))
    total_models = total_models_result.scalar_one()
    
    total_creators_result = await session.execute(
        select(func.count()).select_from(User).where(User.user_type == "creator")
    )
    total_creators = total_creators_result.scalar_one()
    
    total_users_result = await session.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar_one()
    
    # Get featured models (top rated, limit 6)
    featured_query = select(Model).where(Model.status == "approved").order_by(Model.rating.desc()).limit(6)
    featured_result = await session.execute(featured_query)
    featured_models = featured_result.scalars().all()
    
    # Get trending models (most recent, limit 6)
    trending_query = select(Model).where(Model.status == "approved").order_by(Model.created_at.desc()).limit(6)
    trending_result = await session.execute(trending_query)
    trending_models = trending_result.scalars().all()
    
    # Get top creators (by total_models, limit 6)
    top_creators_query = select(User).where(User.user_type == "creator").order_by(User.total_models.desc()).limit(6)
    top_creators_result = await session.execute(top_creators_query)
    top_creators = top_creators_result.scalars().all()
    
    return {
        "featured_models": [ModelResponse.model_validate(m) for m in featured_models],
        "trending_models": [ModelResponse.model_validate(m) for m in trending_models],
        "top_creators": [UserResponse.model_validate(u) for u in top_creators],
        "platform_stats": {
            "total_models": total_models,
            "total_creators": total_creators,
            "total_downloads": 0,  # Downloads tracking not implemented yet
            "total_users": total_users
        }
    }
