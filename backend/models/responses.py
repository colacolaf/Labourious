from typing import Any, Optional
from pydantic import BaseModel


class StandardResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
