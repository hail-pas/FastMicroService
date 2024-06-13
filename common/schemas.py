from pydantic import BaseModel, PositiveInt, conint


class Pager(BaseModel):
    limit: PositiveInt = 10
    offset: conint(ge=0) = 0  # type: ignore


class CURDPager(Pager):
    order_by: set[str] = set()
    search: str | None = None
    selected_fields: set[str] | None = None


class IdsSchema(BaseModel):
    ids: set[str]
