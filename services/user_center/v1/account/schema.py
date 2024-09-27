import uuid

from fastapi import Query
from pydantic import BaseModel


class AccountFilterSchema(BaseModel):
    company_id: uuid.UUID | None = Query(None, description="Company ID")
