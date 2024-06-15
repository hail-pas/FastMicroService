from fastapi import Depends, APIRouter

from services.dependencies import FixedContentQueryChecker

router = APIRouter()

checker = FixedContentQueryChecker("bar")


@router.get("/me")
async def get_current_user(fixed_content_included: bool = Depends(checker)) -> dict:
    return {"username": "burnish", "email": "email@email.com"}
