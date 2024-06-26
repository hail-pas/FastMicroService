import uuid

from fastapi import Query
from pydantic import BaseModel

from common.pydantic import as_query


@as_query
class AccountFilterSchema(BaseModel):
    company_id: uuid.UUID | None = Query(None, description="Company ID")
