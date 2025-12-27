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
    def validate_e164(cls, v):
        if not re.match(r'^\+\d+$', v):
            raise ValueError('Must be E.164 format: start with + followed by digits')
        return v

    @validator('ts')
    def validate_iso8601(cls, v):
        if not v.endswith('Z'):
            raise ValueError('Timestamp must end with Z')
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('Invalid ISO-8601 timestamp')
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
