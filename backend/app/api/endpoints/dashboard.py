import logging
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, update, delete

from app.db.session import get_db, tenant_context
from app.api.deps import get_current_user
from app.models.models import (
    User, Tenant, Conversation, Message, KnowledgeBaseEntry,
    Product, ShopSettings, Channel, AIResponseLog
)
from app.schemas.dashboard import (
    FAQCreate, FAQResponse, ProductCreate, ProductResponse,
    ChannelCreate, ChannelResponse, MessageCreate, MessageResponse,
    ConversationResponse, ConversationUpdate, SettingsResponse, SettingsUpdate,
    AnalyticsResponse, AnalyticsKPIs, AnalyticsChartItem
)

logger = logging.getLogger("replyone.api.dashboard")
router = APIRouter()

# --- CONVERSATIONS & MESSAGES ---

@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    status_filter: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    logger.info(f"Listing conversations for tenant {tenant_id}, filter={status_filter}")
    
    query = select(Conversation).where(Conversation.tenant_id == tenant_id).options(selectinload(Conversation.customer))
    
    if status_filter:
        query = query.where(Conversation.status == status_filter)
        
    query = query.order_by(Conversation.last_message_at.desc())
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Enrich each conversation with its last message content
    res = []
    for conv in conversations:
        # Get last message
        msg_query = select(Message).where(Message.conversation_id == conv.id).order_by(Message.id.desc()).limit(1)
        msg_res = await db.execute(msg_query)
        last_msg = msg_res.scalars().first()
        
        conv_resp = ConversationResponse.from_orm(conv)
        if last_msg:
            conv_resp.last_message = last_msg.content
        res.append(conv_resp)
        
    return res

@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    # Verify conversation ownership
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.tenant_id == tenant_id)
    )
    conv = conv_result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    msg_result = await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at.asc())
    )
    return msg_result.scalars().all()

@router.post("/conversations/{conv_id}/messages", response_model=MessageResponse)
async def send_agent_message(
    conv_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    # Verify conversation ownership
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.tenant_id == tenant_id).options(selectinload(Conversation.customer))
    )
    conv = conv_result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Creating agent outbound message
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=conv_id,
        direction="outbound",
        sender_type="agent",
        sender_user_id=current_user.id,
        content=payload.content,
        delivery_status="sent"
    )
    db.add(msg)
    
    # Update conversation status: deactivate AI autopilot when agent manually replies
    conv.last_message_at = datetime.datetime.utcnow()
    conv.ai_active = False # Agent took over
    conv.status = "open" # Mark as open chat
    db.add(conv)
    
    await db.commit()
    await db.refresh(msg)
    
    # Broadcast updates via WebSocket
    try:
        from app.core.websocket import publish_websocket_event
        
        msg_data = {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "direction": msg.direction,
            "sender_type": msg.sender_type,
            "sender_user_id": msg.sender_user_id,
            "content": msg.content,
            "attachment_url": msg.attachment_url,
            "external_message_id": msg.external_message_id,
            "delivery_status": msg.delivery_status,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "customer_session_id": conv.customer.external_user_id if conv.customer else None
        }
        await publish_websocket_event(tenant_id, "message_created", msg_data)

        cust_data = {
            "id": conv.customer.id,
            "display_name": conv.customer.display_name,
            "avatar_url": conv.customer.avatar_url,
            "phone": conv.customer.phone,
            "external_user_id": conv.customer.external_user_id
        } if conv.customer else None

        conv_data = {
            "id": conv.id,
            "customer_id": conv.customer_id,
            "channel_id": conv.channel_id,
            "channel": conv.channel,
            "status": conv.status,
            "assigned_agent_id": conv.assigned_agent_id,
            "ai_active": conv.ai_active,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "customer": cust_data,
            "last_message": msg.content
        }
        await publish_websocket_event(tenant_id, "conversation_updated", conv_data)
    except Exception as e:
        logger.error(f"Failed to publish WebSocket events in send_agent_message: {e}", exc_info=True)
        
    logger.info(f"Agent {current_user.id} replied to conversation {conv_id}. Handed over from AI.")
    return msg

@router.put("/conversations/{conv_id}", response_model=ConversationResponse)
async def update_conversation(
    conv_id: int,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.tenant_id == tenant_id).options(selectinload(Conversation.customer))
    )
    conv = conv_result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if payload.status is not None:
        conv.status = payload.status
        if payload.status == "resolved":
            conv.resolved_at = datetime.datetime.utcnow()
    if payload.ai_active is not None:
        conv.ai_active = payload.ai_active
    if payload.assigned_agent_id is not None:
        conv.assigned_agent_id = payload.assigned_agent_id
        
    conv.updated_at = datetime.datetime.utcnow()
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    
    # Fetch last message
    msg_query = select(Message).where(Message.conversation_id == conv.id).order_by(Message.id.desc()).limit(1)
    msg_res = await db.execute(msg_query)
    last_msg = msg_res.scalars().first()
    
    # Broadcast updates via WebSocket
    try:
        from app.core.websocket import publish_websocket_event
        
        cust_data = {
            "id": conv.customer.id,
            "display_name": conv.customer.display_name,
            "avatar_url": conv.customer.avatar_url,
            "phone": conv.customer.phone,
            "external_user_id": conv.customer.external_user_id
        } if conv.customer else None

        conv_data = {
            "id": conv.id,
            "customer_id": conv.customer_id,
            "channel_id": conv.channel_id,
            "channel": conv.channel,
            "status": conv.status,
            "assigned_agent_id": conv.assigned_agent_id,
            "ai_active": conv.ai_active,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "customer": cust_data,
            "last_message": last_msg.content if last_msg else None
        }
        await publish_websocket_event(tenant_id, "conversation_updated", conv_data)
    except Exception as e:
        logger.error(f"Failed to publish WebSocket events in update_conversation: {e}", exc_info=True)
        
    conv_resp = ConversationResponse.from_orm(conv)
    if last_msg:
        conv_resp.last_message = last_msg.content
    return conv_resp


# --- KNOWLEDGE BASE (FAQs) ---

@router.get("/knowledge-base", response_model=list[FAQResponse])
async def list_faqs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.tenant_id == tenant_id).order_by(KnowledgeBaseEntry.id.desc())
    )
    return result.scalars().all()

@router.post("/knowledge-base", response_model=FAQResponse)
async def create_faq(
    payload: FAQCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    faq = KnowledgeBaseEntry(
        tenant_id=tenant_id,
        category=payload.category,
        question=payload.question,
        content=payload.content,
        is_active=payload.is_active
    )
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq

@router.put("/knowledge-base/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: int,
    payload: FAQCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.id == faq_id, KnowledgeBaseEntry.tenant_id == tenant_id)
    )
    faq = result.scalars().first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
        
    faq.category = payload.category
    faq.question = payload.question
    faq.content = payload.content
    faq.is_active = payload.is_active
    faq.updated_at = datetime.datetime.utcnow()
    
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq

@router.delete("/knowledge-base/{faq_id}")
async def delete_faq(
    faq_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.id == faq_id, KnowledgeBaseEntry.tenant_id == tenant_id)
    )
    faq = result.scalars().first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
        
    await db.delete(faq)
    await db.commit()
    return {"message": "FAQ entry deleted successfully"}


# --- PRODUCTS CATALOG ---

@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(Product).where(Product.tenant_id == tenant_id).order_by(Product.id.desc())
    )
    return result.scalars().all()

@router.post("/products", response_model=ProductResponse)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    product = Product(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        stock_status=payload.stock_status,
        image_url=payload.image_url,
        is_active=payload.is_active
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

@router.put("/products/{prod_id}", response_model=ProductResponse)
async def update_product(
    prod_id: int,
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(Product).where(Product.id == prod_id, Product.tenant_id == tenant_id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    product.name = payload.name
    product.description = payload.description
    product.price = payload.price
    product.currency = payload.currency
    product.stock_status = payload.stock_status
    product.image_url = payload.image_url
    product.is_active = payload.is_active
    product.updated_at = datetime.datetime.utcnow()
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/products/{prod_id}")
async def delete_product(
    prod_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(Product).where(Product.id == prod_id, Product.tenant_id == tenant_id)
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    await db.delete(product)
    await db.commit()
    return {"message": "Product deleted successfully"}


# --- SHOP SETTINGS ---

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(ShopSettings).where(ShopSettings.tenant_id == tenant_id)
    )
    settings = result.scalars().first()
    if not settings:
        # Create default settings if not exists
        settings = ShopSettings(
            tenant_id=tenant_id,
            ai_tone="balanced",
            ai_auto_reply_enabled=True,
            ai_confidence_threshold=0.700
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
    return settings

@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(ShopSettings).where(ShopSettings.tenant_id == tenant_id)
    )
    settings = result.scalars().first()
    if not settings:
        settings = ShopSettings(tenant_id=tenant_id)
        
    if payload.ai_tone is not None:
        settings.ai_tone = payload.ai_tone
    if payload.ai_auto_reply_enabled is not None:
        settings.ai_auto_reply_enabled = payload.ai_auto_reply_enabled
    if payload.ai_confidence_threshold is not None:
        settings.ai_confidence_threshold = payload.ai_confidence_threshold
    if payload.notify_email_on_escalation is not None:
        settings.notify_email_on_escalation = payload.notify_email_on_escalation
    if payload.notify_push_on_escalation is not None:
        settings.notify_push_on_escalation = payload.notify_push_on_escalation
    if payload.business_hours_json is not None:
        settings.business_hours_json = payload.business_hours_json
        
    settings.updated_at = datetime.datetime.utcnow()
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    
    # Keep Tenant AI settings in sync with ShopSettings
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalars().first()
    if tenant:
        tenant.ai_enabled = settings.ai_auto_reply_enabled
        tenant.ai_confidence_threshold = int(settings.ai_confidence_threshold * 100)
        db.add(tenant)
        await db.commit()
        
    return settings


# --- CHANNELS & ONBOARDING ---

@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    result = await db.execute(
        select(Channel).where(Channel.tenant_id == tenant_id)
    )
    return result.scalars().all()

@router.post("/channels", response_model=ChannelResponse)
async def create_channel(
    payload: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    
    # Check if channel type already exists
    exists_check = await db.execute(
        select(Channel).where(Channel.tenant_id == tenant_id, Channel.channel_type == payload.channel_type)
    )
    existing = exists_check.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail=f"A channel of type {payload.channel_type} is already configured.")
        
    channel = Channel(
        tenant_id=tenant_id,
        channel_type=payload.channel_type,
        external_account_id=payload.external_account_id or "mock_acc_id",
        access_token_encrypted=payload.access_token_encrypted,
        webhook_verify_token=payload.webhook_verify_token,
        widget_config_json=payload.widget_config_json,
        status="connected",
        connected_at=datetime.datetime.utcnow()
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel

@router.post("/onboarding/complete")
async def complete_onboarding(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    tenant.onboarding_complete = True
    db.add(tenant)
    await db.commit()
    return {"status": "success", "message": "Onboarding complete"}


# --- ANALYTICS ---

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant_id = current_user.tenant_id
    
    # Count conversations
    t_convs_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id)
    )
    total_conversations = t_convs_result.scalar() or 0
    
    # Count messages
    t_msgs_result = await db.execute(
        select(func.count(Message.id)).where(Message.tenant_id == tenant_id)
    )
    total_messages = t_msgs_result.scalar() or 0
    
    # Count escalated conversations
    esc_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id, Conversation.status == "escalated")
    )
    escalated_conversations = esc_result.scalar() or 0
    
    # Count resolved conversations
    res_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id, Conversation.status == "resolved")
    )
    resolved_conversations = res_result.scalar() or 0
    
    # Count AI replies (messages outbound and sender_type="ai")
    ai_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.tenant_id == tenant_id,
            Message.direction == "outbound",
            Message.sender_type == "ai"
        )
    )
    ai_auto_replies = ai_result.scalar() or 0
    
    # Average Latency from logs
    lat_result = await db.execute(
        select(func.avg(AIResponseLog.latency_ms)).where(AIResponseLog.tenant_id == tenant_id)
    )
    avg_latency = lat_result.scalar()
    avg_latency_ms = int(avg_latency) if avg_latency is not None else 150
    
    kpis = AnalyticsKPIs(
        total_conversations=total_conversations,
        total_messages=total_messages,
        ai_auto_replies=ai_auto_replies,
        escalated_conversations=escalated_conversations,
        resolved_conversations=resolved_conversations,
        avg_latency_ms=avg_latency_ms
    )
    
    # Generate mock daily timeline chart data for the past 7 days
    chart_data = []
    base_date = datetime.date.today()
    
    # Look back 7 days
    for i in range(6, -1, -1):
        day = base_date - datetime.timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        # We can dynamically distribute counts for realism, centered around the database totals
        # In a real app we'd group by day in SQL.
        # But this mock gives stable visual rendering for chart elements.
        factor = (i + 1) * 3
        chart_data.append(
            AnalyticsChartItem(
                date=day_str,
                conversations=max(1, int(total_conversations / 7) + (factor % 4) - 2),
                messages=max(2, int(total_messages / 7) + (factor % 7) - 3),
                auto_replies=max(0, int(ai_auto_replies / 7) + (factor % 3) - 1),
                escalations=max(0, int(escalated_conversations / 7) + (factor % 2))
            )
        )
        
    return AnalyticsResponse(kpis=kpis, chart_data=chart_data)
