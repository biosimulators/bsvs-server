from datetime import datetime

from pydantic import BaseModel


class ListingItem(BaseModel):
    Key: str
    LastModified: datetime
    ETag: str
    Size: int
