from pydantic import BaseModel
from typing import Optional, Any


class RelayResponse(BaseModel):
    status: str
    data: Optional[Any] = None
    violation: Optional[dict] = None
