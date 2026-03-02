from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.transaction_repository import TransactionRepository

router = APIRouter()


@router.get("/{transaction_id}")
async def get_purchase_details(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get purchase details"""
    # TODO: Implement purchase retrieval
    return {
        "transaction_id": transaction_id,
        "status": "completed",
        "models": []
    }


@router.get("/{transaction_id}/download-link")
async def get_download_link(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get download link for purchased models"""
    # TODO: Generate signed download URLs
    return {
        "download_url": "https://cdn.sdmodels.com/downloads/signed-url",
        "expires_at": "2024-02-17T00:00:00Z"
    }
