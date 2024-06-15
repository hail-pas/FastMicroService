from fastapi import Depends

from services.dependencies import FixedContentQueryChecker
from services.userCenter.routers.v1.account import router

checker = FixedContentQueryChecker("bar")


@router.get("/me")
async def get_current_user(fixed_content_included: bool = Depends(checker)) -> dict:
    return {"username": "phoenix", "email": "email@email.com"}
