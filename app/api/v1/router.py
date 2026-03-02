from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, models, communities, transactions, support, admin,
    blog, search, notifications, collections, messages, dashboard, upload, stats,
    pricing, help, docs, checkout, purchases, bounties, admin_bounties, admin_auth, wallet, bounty_chat, payments, admin_support
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(models.router, prefix="/models", tags=["Models"])
api_router.include_router(communities.router, prefix="/communities", tags=["Communities"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(support.router, prefix="/support", tags=["Support"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(blog.router, prefix="/blog", tags=["Blog"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(collections.router, prefix="/collections", tags=["Collections"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(stats.router, prefix="/stats", tags=["Stats"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["Pricing"])
api_router.include_router(help.router, prefix="/help", tags=["Help"])
api_router.include_router(docs.router, prefix="/docs", tags=["Docs"])
api_router.include_router(checkout.router, prefix="/checkout", tags=["Checkout"])
api_router.include_router(purchases.router, prefix="/purchases", tags=["Purchases"])
api_router.include_router(bounties.router, prefix="/bounties", tags=["Bounties"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
api_router.include_router(bounty_chat.router, prefix="/bounty-chat", tags=["Bounty Chat"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(admin_auth.router, prefix="/admin/auth", tags=["Admin Authentication"])
api_router.include_router(admin_bounties.router, prefix="/admin", tags=["Admin Bounties"])
api_router.include_router(admin_support.router, prefix="/admin/support", tags=["Admin Support"])
