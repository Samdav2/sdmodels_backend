from typing import Optional, List
from uuid import UUID
import json
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.model_repository import ModelRepository
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse


class ModelService:
    def __init__(self, session: AsyncSession):
        self.model_repo = ModelRepository(session)
    
    async def create_model(self, creator_id: UUID, model_data: ModelCreate) -> ModelResponse:
        # Convert lists to JSON strings for database storage
        data_dict = model_data.model_dump()
        data_dict['tags'] = json.dumps(data_dict.get('tags', []))
        data_dict['preview_images'] = json.dumps(data_dict.get('preview_images', []))
        data_dict['file_formats'] = json.dumps(data_dict.get('file_formats', []))
        
        model = await self.model_repo.create(
            creator_id=creator_id,
            **data_dict
        )
        return model
    
    async def get_model(self, model_id: UUID) -> ModelResponse:
        model_dict = await self.model_repo.get_by_id(model_id)
        if not model_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        # Parse JSON fields if they're strings
        if isinstance(model_dict.get('tags'), str):
            model_dict['tags'] = json.loads(model_dict['tags']) if model_dict['tags'] else []
        if isinstance(model_dict.get('preview_images'), str):
            model_dict['preview_images'] = json.loads(model_dict['preview_images']) if model_dict['preview_images'] else []
        if isinstance(model_dict.get('file_formats'), str):
            model_dict['file_formats'] = json.loads(model_dict['file_formats']) if model_dict['file_formats'] else []
        
        return ModelResponse(**model_dict)
    
    async def get_models(
        self,
        page: int = 1,
        limit: int = 20,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_free: Optional[bool] = None,
        search: Optional[str] = None,
        sort: str = "newest"
    ) -> dict:
        skip = (page - 1) * limit
        models_data, total = await self.model_repo.get_all(
            skip=skip,
            limit=limit,
            category=category,
            min_price=min_price,
            max_price=max_price,
            is_free=is_free,
            search=search,
            sort=sort
        )
        
        # Convert dict data to ModelResponse objects
        models = []
        for model_dict in models_data:
            # Parse JSON fields if they're strings
            if isinstance(model_dict.get('tags'), str):
                model_dict['tags'] = json.loads(model_dict['tags']) if model_dict['tags'] else []
            if isinstance(model_dict.get('preview_images'), str):
                model_dict['preview_images'] = json.loads(model_dict['preview_images']) if model_dict['preview_images'] else []
            if isinstance(model_dict.get('file_formats'), str):
                model_dict['file_formats'] = json.loads(model_dict['file_formats']) if model_dict['file_formats'] else []
            
            models.append(ModelResponse(**model_dict))
        
        return {
            "models": models,
            "total": total,
            "page": page,
            "limit": limit
        }
    
    async def update_model(self, model_id: UUID, creator_id: UUID, model_data: ModelUpdate) -> ModelResponse:
        model = await self.model_repo.get_model_object(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        if model.creator_id != creator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this model"
            )
        
        # Convert lists to JSON strings for database storage
        data_dict = model_data.model_dump(exclude_unset=True)
        if 'tags' in data_dict:
            data_dict['tags'] = json.dumps(data_dict['tags'])
        if 'preview_images' in data_dict:
            data_dict['preview_images'] = json.dumps(data_dict['preview_images'])
        if 'file_formats' in data_dict:
            data_dict['file_formats'] = json.dumps(data_dict['file_formats'])
        
        updated_model = await self.model_repo.update(model_id, **data_dict)
        
        # Get the updated model with username
        model_dict = await self.model_repo.get_by_id(model_id)
        if isinstance(model_dict.get('tags'), str):
            model_dict['tags'] = json.loads(model_dict['tags']) if model_dict['tags'] else []
        if isinstance(model_dict.get('preview_images'), str):
            model_dict['preview_images'] = json.loads(model_dict['preview_images']) if model_dict['preview_images'] else []
        if isinstance(model_dict.get('file_formats'), str):
            model_dict['file_formats'] = json.loads(model_dict['file_formats']) if model_dict['file_formats'] else []
        
        return ModelResponse(**model_dict)
    
    async def delete_model(self, model_id: UUID, creator_id: UUID) -> bool:
        model = await self.model_repo.get_model_object(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        if model.creator_id != creator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this model"
            )
        
        return await self.model_repo.delete(model_id)
    
    async def like_model(self, user_id: UUID, model_id: UUID):
        model = await self.model_repo.get_model_object(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        return await self.model_repo.like_model(user_id, model_id)
    
    async def unlike_model(self, user_id: UUID, model_id: UUID):
        return await self.model_repo.unlike_model(user_id, model_id)
    
    async def add_comment(self, user_id: UUID, model_id: UUID, content: str, parent_id: Optional[UUID] = None):
        model = await self.model_repo.get_model_object(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        comment = await self.model_repo.add_comment(user_id, model_id, content, parent_id)
        
        # Send email to model owner if someone else commented
        if model.creator_id != user_id:
            try:
                from app.utils.email import send_model_comment_email
                from app.core.config import settings
                from sqlalchemy import select
                from app.models.user import User
                
                # Get owner and commenter info
                owner_result = await self.model_repo.session.execute(
                    select(User).where(User.id == model.creator_id)
                )
                owner = owner_result.scalar_one_or_none()
                
                commenter_result = await self.model_repo.session.execute(
                    select(User).where(User.id == user_id)
                )
                commenter = commenter_result.scalar_one_or_none()
                
                if owner and commenter:
                    await send_model_comment_email(
                        user_email=owner.email,
                        username=owner.username,
                        commenter_username=commenter.username,
                        model_title=model.title,
                        comment_content=content[:200],  # First 200 chars
                        model_url=f"{settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'}/models/{model_id}"
                    )
            except Exception as e:
                print(f"Failed to send comment email: {e}")
        
        return comment
    
    async def get_comments(self, model_id: UUID, page: int = 1, limit: int = 50):
        skip = (page - 1) * limit
        return await self.model_repo.get_comments(model_id, skip, limit)
    
    async def increment_view(self, model_id: UUID):
        return await self.model_repo.increment_views(model_id)
