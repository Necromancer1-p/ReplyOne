from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from decimal import Decimal

# --- FAQ Schemas ---
class FAQCreate(BaseModel):
    category: str = Field(..., description="Hours, shipping, returns, faq, general")
    question: str = Field(..., max_length=500)
    content: str
    is_active: bool = True

class FAQResponse(BaseModel):
    id: int
    tenant_id: int
    category: str
    question: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Product Schemas ---
class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = None
    currency: str = "INR"
    stock_status: str = "in_stock"
    image_url: Optional[str] = None
    is_active: bool = True

class ProductResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    description: Optional[str]
    price: Optional[Decimal]
    currency: str
    stock_status: str
    image_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Channel Schemas ---
class ChannelCreate(BaseModel):
    channel_type: str = Field(..., description="whatsapp, instagram, website")
    external_account_id: Optional[str] = None
    access_token_encrypted: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    widget_config_json: Optional[Any] = None

class ChannelResponse(BaseModel):
    id: int
    tenant_id: int
    channel_type: str
    external_account_id: Optional[str]
    status: str
    connected_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Customer Schema for Inbox ---
class CustomerInfo(BaseModel):
    id: int
    display_name: Optional[str]
    avatar_url: Optional[str]
    phone: Optional[str]
    external_user_id: str

    class Config:
        from_attributes = True


# --- Message Schemas ---
class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    direction: str
    sender_type: str
    sender_user_id: Optional[int]
    content: str
    attachment_url: Optional[str]
    external_message_id: Optional[str]
    delivery_status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Conversation Schemas ---
class ConversationResponse(BaseModel):
    id: int
    customer_id: int
    channel_id: int
    channel: str
    status: str
    assigned_agent_id: Optional[int]
    ai_active: bool
    last_message_at: datetime
    created_at: datetime
    customer: CustomerInfo
    last_message: Optional[str] = None

    class Config:
        from_attributes = True

class ConversationUpdate(BaseModel):
    status: Optional[str] = None
    ai_active: Optional[bool] = None
    assigned_agent_id: Optional[int] = None


# --- Shop Settings Schemas ---
class SettingsResponse(BaseModel):
    tenant_id: int
    ai_tone: str
    ai_auto_reply_enabled: bool
    ai_confidence_threshold: float
    notify_email_on_escalation: bool
    notify_push_on_escalation: bool
    business_hours_json: Optional[Any]
    updated_at: datetime

    class Config:
        from_attributes = True

class SettingsUpdate(BaseModel):
    ai_tone: Optional[str] = None
    ai_auto_reply_enabled: Optional[bool] = None
    ai_confidence_threshold: Optional[float] = None
    notify_email_on_escalation: Optional[bool] = None
    notify_push_on_escalation: Optional[bool] = None
    business_hours_json: Optional[Any] = None


# --- Analytics Schemas ---
class AnalyticsKPIs(BaseModel):
    total_conversations: int
    total_messages: int
    ai_auto_replies: int
    escalated_conversations: int
    resolved_conversations: int
    avg_latency_ms: int

class AnalyticsChartItem(BaseModel):
    date: str
    conversations: int
    messages: int
    auto_replies: int
    escalations: int

class AnalyticsResponse(BaseModel):
    kpis: AnalyticsKPIs
    chart_data: List[AnalyticsChartItem]
