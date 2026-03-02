from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/plans")
async def get_pricing_plans(session: AsyncSession = Depends(get_session)):
    """Get pricing plans"""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price": 0,
                "features": ["Upload up to 5 models", "Basic analytics"]
            },
            {
                "id": "pro",
                "name": "Pro",
                "price": 29,
                "features": ["Unlimited uploads", "Advanced analytics", "Priority support"]
            }
        ]
    }


@router.post("/subscribe")
async def subscribe_to_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Subscribe to a plan"""
    return {"message": "Subscription successful", "plan_id": plan_id}


@router.put("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Cancel subscription"""
    return {"message": "Subscription cancelled"}
