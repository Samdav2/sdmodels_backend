from typing import Optional, List
from uuid import UUID
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model import Model, ModelLike, ModelComment


class ModelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, **kwargs) -> Model:
        model = Model(**kwargs)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model
    
    async def get_by_id(self, model_id: UUID) -> Optional[dict]:
        from app.models.user import User
        
        result = await self.session.execute(
            select(Model, User.username).join(
                User, Model.creator_id == User.id
            ).where(Model.id == model_id)
        )
        row = result.first()
        
        if not row:
            return None
        
        model, username = row
        model_dict = {
            **model.__dict__,
            'creator_username': username
        }
        return model_dict
    
    async def get_model_object(self, model_id: UUID) -> Optional[Model]:
        """Get raw model object for update/delete operations"""
        result = await self.session.execute(
            select(Model).where(Model.id == model_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_free: Optional[bool] = None,
        search: Optional[str] = None,
        sort: str = "newest"
    ) -> tuple[List[dict], int]:
        from app.models.user import User
        
        query = select(Model, User.username).join(
            User, Model.creator_id == User.id
        ).where(Model.is_published == True)
        
        if category:
            query = query.where(Model.category == category)
        
        if min_price is not None:
            query = query.where(Model.price >= min_price)
        
        if max_price is not None:
            query = query.where(Model.price <= max_price)
        
        if is_free is not None:
            query = query.where(Model.is_free == is_free)
        
        if search:
            query = query.where(
                (Model.title.ilike(f"%{search}%")) | 
                (Model.description.ilike(f"%{search}%"))
            )
        
        # Sorting
        if sort == "newest":
            query = query.order_by(Model.created_at.desc())
        elif sort == "popular":
            query = query.order_by(Model.views.desc())
        elif sort == "price_low":
            query = query.order_by(Model.price.asc())
        elif sort == "price_high":
            query = query.order_by(Model.price.desc())
        
        # Get total count
        count_query = select(func.count()).select_from(
            select(Model).join(User, Model.creator_id == User.id).where(Model.is_published == True).subquery()
        )
        if category:
            count_query = select(func.count()).select_from(
                select(Model).join(User, Model.creator_id == User.id).where(
                    Model.is_published == True,
                    Model.category == category
                ).subquery()
            )
        
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        rows = result.all()
        
        # Convert to list of dicts with creator_username
        models = []
        for model, username in rows:
            model_dict = {
                **model.__dict__,
                'creator_username': username
            }
            models.append(model_dict)
        
        return models, total
    
    async def update(self, model_id: UUID, **kwargs) -> Optional[Model]:
        model = await self.get_model_object(model_id)
        if not model:
            return None
        
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        await self.session.commit()
        await self.session.refresh(model)
        return model
    
    async def delete(self, model_id: UUID) -> bool:
        model = await self.get_model_object(model_id)
        if not model:
            return False
        
        await self.session.delete(model)
        await self.session.commit()
        return True
    
    async def increment_views(self, model_id: UUID) -> bool:
        model = await self.get_model_object(model_id)
        if not model:
            return False
        
        model.views += 1
        await self.session.commit()
        return True
    
    async def like_model(self, user_id: UUID, model_id: UUID) -> ModelLike:
        like = ModelLike(user_id=user_id, model_id=model_id)
        self.session.add(like)
        
        # Increment likes count
        model = await self.get_model_object(model_id)
        if model:
            model.likes += 1
        
        await self.session.commit()
        await self.session.refresh(like)
        return like
    
    async def unlike_model(self, user_id: UUID, model_id: UUID) -> bool:
        result = await self.session.execute(
            select(ModelLike).where(
                ModelLike.user_id == user_id,
                ModelLike.model_id == model_id
            )
        )
        like = result.scalar_one_or_none()
        
        if not like:
            return False
        
        await self.session.delete(like)
        
        # Decrement likes count
        model = await self.get_model_object(model_id)
        if model and model.likes > 0:
            model.likes -= 1
        
        await self.session.commit()
        return True
    
    async def add_comment(self, user_id: UUID, model_id: UUID, content: str, parent_id: Optional[UUID] = None) -> ModelComment:
        comment = ModelComment(
            user_id=user_id,
            model_id=model_id,
            content=content,
            parent_id=parent_id
        )
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment
    
    async def get_comments(self, model_id: UUID, skip: int = 0, limit: int = 50) -> List[ModelComment]:
        result = await self.session.execute(
            select(ModelComment)
            .where(ModelComment.model_id == model_id)
            .order_by(ModelComment.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_creator(self, creator_id: UUID, skip: int = 0, limit: int = 20) -> List[Model]:
        result = await self.session.execute(
            select(Model)
            .where(Model.creator_id == creator_id)
            .order_by(Model.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
