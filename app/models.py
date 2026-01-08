import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator

class WebhookMessage(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from")
    to: str
    ts: str
    text: Optional[str] = Field(None, max_length=4096)

    @validator('from_', 'to')
    def validate_indian_phone(cls, v):
        if not re.match(r'^\+91[6-9]\d{9}$', v):
            raise ValueError('Must be valid Indian number: +91 followed by 10 digits')
        return v


    @validator('ts')
    def validate_ist_timestamp(cls, v):
        if not v.endswith('+05:30'):
            raise ValueError('Timestamp must be in IST (+05:30)')
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError('Invalid ISO-8601 IST timestamp')
        return v


class MessageResponse(BaseModel):
    message_id: str
    from_: str = Field(..., alias="from")
    to: str
    ts: str
    text: Optional[str] = None

    class Config:
        populate_by_name = True

class MessagesListResponse(BaseModel):
    data: list[MessageResponse]
    total: int
    limit: int
    offset: int

class SenderCount(BaseModel):
    from_: str = Field(..., alias="from")
    count: int

    class Config:
        populate_by_name = True

class StatsResponse(BaseModel):
    total_messages: int
    senders_count: int
    messages_per_sender: list[SenderCount]
    first_message_ts: Optional[str]
    last_message_ts: Optional[str]
