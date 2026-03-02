from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter()


@router.get("/faqs")
async def get_faqs(
    category: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get FAQs"""
    return {"faqs": []}


@router.get("/categories")
async def get_help_categories(session: AsyncSession = Depends(get_session)):
    """Get help categories"""
    return {
        "categories": [
            "Getting Started",
            "Uploading Models",
            "Payments",
            "Account Settings"
        ]
    }
