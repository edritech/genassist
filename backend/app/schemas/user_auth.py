from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.operator_auth import OperatorAuth


class UserAuth(BaseModel):
    id: UUID
    force_upd_pass_date: Optional[datetime] = None
    operator: Optional[OperatorAuth] = None

    model_config = ConfigDict(from_attributes=True)
