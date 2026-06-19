import datetime
import logging
from sqlalchemy import (
    Column, Integer, String, Enum, DateTime, Boolean,
    ForeignKey, Text, JSON, Numeric, UniqueConstraint, Index
)
# Alias BigInteger to Integer for SQLite autoincrement compatibility
BigInteger = Integer

from sqlalchemy.orm import relationship
from app.db.session import Base

logger = logging.getLogger("replyone.models")
logger.info("Initializing database models...")

# --- TENANT ---
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    plan = Column(Enum("trial", "starter", "growth", "enterprise", name="plan_enum"), nullable=False, default="trial")
    ai_enabled = Column(Boolean, nullable=False, default=True)
    ai_confidence_threshold = Column(Integer, nullable=False, default=70) # percentage
    timezone = Column(String(60), nullable=False, default="Asia/Kolkata")
    stripe_customer_id = Column(String(40), nullable=True)
    onboarding_complete = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    channels = relationship("Channel", back_populates="tenant", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="tenant", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="tenant", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="tenant", cascade="all, delete-orphan")
    knowledge_base_entries = relationship("KnowledgeBaseEntry", back_populates="tenant", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="tenant", cascade="all, delete-orphan")
    quick_reply_templates = relationship("QuickReplyTemplate", back_populates="tenant", cascade="all, delete-orphan")
    shop_settings = relationship("ShopSettings", uselist=False, back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant id={self.id} name='{self.name}' slug='{self.slug}'>"


# --- USER & SESSION ---
class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(200), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("owner", "agent", "viewer", name="role_enum"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    password_resets = relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan")
    assigned_conversations = relationship("Conversation", back_populates="assigned_agent")
    assignments = relationship("ConversationAssignment", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(String(255), nullable=False, index=True)
    device_label = Column(String(150), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="password_resets")


# --- CHANNEL & CUSTOMER ---
class Channel(Base):
    __tablename__ = "channels"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    channel_type = Column(Enum("whatsapp", "instagram", "website", name="channel_type_enum"), nullable=False)
    external_account_id = Column(String(255), nullable=True)
    access_token_encrypted = Column(Text, nullable=True)
    webhook_verify_token = Column(String(255), nullable=True)
    widget_config_json = Column(JSON, nullable=True)
    status = Column(Enum("connected", "disconnected", "error", "pending", name="channel_status_enum"), nullable=False, default="pending")
    last_event_at = Column(DateTime, nullable=True)
    connected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "channel_type", name="uq_tenant_channel_type"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="channels")
    customers = relationship("Customer", back_populates="channel")
    conversations = relationship("Conversation", back_populates="channel_rel")
    webhook_events = relationship("WebhookEvent", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Channel id={self.id} type='{self.channel_type}' status='{self.status}'>"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(BigInteger, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    external_user_id = Column(String(255), nullable=False)
    display_name = Column(String(150), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    first_seen_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "channel_id", "external_user_id", name="uq_tenant_channel_customer"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="customers")
    channel = relationship("Channel", back_populates="customers")
    conversations = relationship("Conversation", back_populates="customer", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(BigInteger, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(BigInteger, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    channel = Column(Enum("whatsapp", "instagram", "widget", name="conv_channel_enum"), nullable=False)
    status = Column(Enum("open", "pending", "resolved", "escalated", name="conv_status_enum"), nullable=False, default="open")
    assigned_agent_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ai_active = Column(Boolean, nullable=False, default=True)
    last_message_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="conversations")
    customer = relationship("Customer", back_populates="conversations")
    assigned_agent = relationship("User", back_populates="assigned_conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    assignments = relationship("ConversationAssignment", back_populates="conversation", cascade="all, delete-orphan")
    channel_rel = relationship("Channel", back_populates="conversations", foreign_keys=[channel_id])


class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    direction = Column(Enum("inbound", "outbound", name="message_direction_enum"), nullable=False)
    sender_type = Column(Enum("customer", "agent", "ai", name="sender_type_enum"), nullable=False)
    sender_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    external_message_id = Column(String(255), nullable=True)
    delivery_status = Column(Enum("sent", "delivered", "read", "failed", name="delivery_status_enum"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
    ai_response_log = relationship("AIResponseLog", uselist=False, back_populates="message", cascade="all, delete-orphan")


class AIResponseLog(Base):
    __tablename__ = "ai_response_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), unique=True, nullable=False)
    intent_classified = Column(String(100), nullable=False)
    sentiment = Column(Enum("positive", "neutral", "negative", "urgent", name="sentiment_enum"), nullable=False)
    confidence_score = Column(Numeric(4, 3), nullable=False) # 0.000 to 1.000
    knowledge_sources_used = Column(JSON, nullable=True)
    model_name = Column(String(100), nullable=False)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    message = relationship("Message", back_populates="ai_response_log")


class ConversationAssignment(Base):
    __tablename__ = "conversation_assignments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(Enum("took_over", "handed_back_to_ai", "resolved", name="assignment_action_enum"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="assignments")
    user = relationship("User", back_populates="assignments")


# --- KNOWLEDGE BASE & PRODUCTS ---
class Product(Base):
    __tablename__ = "products"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="INR")
    stock_status = Column(Enum("in_stock", "out_of_stock", "limited", name="stock_status_enum"), nullable=False, default="in_stock")
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="products")


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base_entries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    category = Column(Enum("hours", "shipping", "returns", "faq", "general", name="kb_category_enum"), nullable=False)
    question = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="knowledge_base_entries")


class QuickReplyTemplate(Base):
    __tablename__ = "quick_reply_templates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    intent_tag = Column(String(100), nullable=False)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="quick_reply_templates")


# --- SHOP SETTINGS ---
class ShopSettings(Base):
    __tablename__ = "shop_settings"

    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    ai_tone = Column(Enum("formal", "balanced", "friendly", name="ai_tone_enum"), nullable=False, default="balanced")
    ai_auto_reply_enabled = Column(Boolean, nullable=False, default=True)
    ai_confidence_threshold = Column(Numeric(4, 3), nullable=False, default=0.700)
    notify_email_on_escalation = Column(Boolean, nullable=False, default=True)
    notify_push_on_escalation = Column(Boolean, nullable=False, default=True)
    business_hours_json = Column(JSON, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="shop_settings")


# --- SUBSCRIPTION ---
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    plan_tier = Column(Enum("free", "starter", "growth", "enterprise", name="plan_tier_enum"), nullable=False, default="free")
    external_subscription_id = Column(String(255), nullable=True)
    status = Column(Enum("active", "past_due", "cancelled", "trialing", name="sub_status_enum"), nullable=False, default="trialing")
    messages_used_this_period = Column(Integer, nullable=False, default=0)
    message_quota = Column(Integer, nullable=False, default=500)
    current_period_start = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    current_period_end = Column(DateTime, nullable=False, default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=14))
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="subscriptions")


# --- AUDIT & WEBHOOK EVENTS ---
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(150), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    raw_payload_json = Column(JSON, nullable=False)
    processing_status = Column(Enum("pending", "processed", "failed", name="proc_status_enum"), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationships
    channel = relationship("Channel", back_populates="webhook_events")


logger.info("Database models initialized successfully.")
