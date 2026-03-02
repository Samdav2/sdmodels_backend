from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter()


@router.get("/sections")
async def get_doc_sections(session: AsyncSession = Depends(get_session)):
    """Get documentation sections"""
    return {
        "sections": [
            {"id": "getting-started", "title": "Getting Started"},
            {"id": "api-reference", "title": "API Reference"},
            {"id": "tutorials", "title": "Tutorials"}
        ]
    }


@router.get("/{section}")
async def get_doc_section(
    section: str,
    session: AsyncSession = Depends(get_session)
):
    """Get documentation section content"""
    return {
        "section": section,
        "title": "Documentation",
        "content": "Documentation content here"
    }
