from fastapi import Path, Query, Depends
from pydantic import Field, BaseModel, ConfigDict, computed_field

from common.types import datetime
from common.responses import Resp
from services.dependencies import FixedContentQueryChecker
from services.userCenter.routers.v1.account import router

checker = FixedContentQueryChecker("bar")


class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, title="用户名", description="用户名")
    email: str = Field(..., min_length=5, max_length=100, description="邮箱")
    born_date: datetime = Field(..., description="出生日期")

    @computed_field
    def age(self) -> int:
        today = datetime.now()
        return (
            today.year - self.born_date.year - ((today.month, today.day) < (self.born_date.month, self.born_date.day))
        )

    model_config = ConfigDict(validation_error_cause=True)


@router.post("/me/{user_id}")
async def get_current_user(
    user: User,
    id: int,
    user_id: str = Path(..., description="用户ID", min_length=3, title="用户ID"),
    fixed_content_included: bool = Depends(checker),
) -> Resp[User]:
    return Resp[User](data=user)


@router.get("/me")
async def get_user_id(
    user_id: str = Query(..., description="用户ID", min_length=3, title="用户ID"),
    fixed_content_included: bool = Depends(checker),
) -> Resp[dict]:
    return Resp[dict](data={"user_id": user_id})
