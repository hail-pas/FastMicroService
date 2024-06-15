from fastapi import APIRouter

from services.userCenter.routers.v1.account.views import router as account_router

router = APIRouter(prefix="/v1")

router.include_router(account_router, prefix="/account", tags=["account"])
