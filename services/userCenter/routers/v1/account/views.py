from typing import Annotated
from decimal import Decimal

from fastapi import Path, Depends
from pydantic import Field, BaseModel, ConfigDict, computed_field

from common.types import datetime
from common.pydantic import as_form
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


@as_form
class DriverFilterSchema(BaseModel):
    username: str | None = Field(None, description="用户名", title="用户名", min_length=3, max_length=50)
    phone: str | None = Field(None, description="手机号", pattern="^[a-zA-Z0-9]+$", title="手机号")
    age: int | None = Field(None, description="年龄", ge=1, le=100, multiple_of=10, title="年龄")
    money: Annotated[Decimal, Field(description="金额", gt=0, lt=100, decimal_places=2, title="金额")]


@router.post("/me1")
async def get_user_id(
    driver_filter: DriverFilterSchema = Depends(DriverFilterSchema.as_form),  # type: ignore
) -> Resp[dict]:
    return Resp[dict](data=driver_filter.dict())
