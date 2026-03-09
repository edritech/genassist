from typing import Dict

from pydantic import BaseModel


class TopicsReport(BaseModel):
    total: int
    details: Dict[str, int]
