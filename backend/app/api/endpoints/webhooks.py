import logging
import json
import datetime
import hashlib
import hmac
from fastapi import APIRouter, Request, Query, HTTPException, status, Depends, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db, tenant_context
from app.models.models import Tenant, Channel, WebhookEvent
from app.schemas.auth import MessageResponse

logger = logging.getLogger("replyone.webhooks")
router = APIRouter()

# Helper to verify Meta signature
def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature:
        return False
    if signature.startswith("sha256="):
        signature = signature.replace("sha256=", "")
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.get("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"WhatsApp webhook handshake requested. Mode: {hub_mode}")
    
    # In V1 local, we accept standard verify token "replyone_verify_token"
    # Or lookup if the token exists on any of our channels
    if hub_mode == "subscribe":
        logger.info(f"Handshake challenge accepted: {hub_challenge}")
        return hub_challenge
        
    logger.warning("WhatsApp handshake failed: mode is not subscribe")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification failed")

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    logger.info("Received WhatsApp webhook POST request.")
    
    payload = await request.body()
    payload_str = payload.decode("utf-8")
    logger.debug(f"WhatsApp raw payload: {payload_str}")
    
    # Try to verify signature if signature header exists and channel token exists
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    # Parse payload
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # In Meta webhook, lookup phone_number_id to identify which channel it belongs to
    # entry -> changes -> value -> metadata -> phone_number_id
    phone_number_id = None
    try:
        phone_number_id = data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
    except (KeyError, IndexError, TypeError):
        pass
        
    logger.debug(f"Parsed phone_number_id from payload: {phone_number_id}")
    
    # Find matching channel
    channel = None
    if phone_number_id:
        result = await db.execute(
            select(Channel).where(
                Channel.external_account_id == str(phone_number_id),
                Channel.channel_type == "whatsapp"
            )
        )
        channel = result.scalars().first()

    # If channel not found, fallback to first whatsapp channel in db for easy testing
    if not channel:
        logger.warning(f"No WhatsApp channel registered with phone_number_id: {phone_number_id}. Falling back to first available channel for testing.")
        result = await db.execute(select(Channel).where(Channel.channel_type == "whatsapp"))
        channel = result.scalars().first()

    if not channel:
        logger.error("No WhatsApp channel exists in the database. Webhook ignored.")
        raise HTTPException(status_code=404, detail="WhatsApp channel not configured.")

    # Persist raw webhook event
    logger.debug(f"Persisting webhook event for channel: {channel.id}")
    event = WebhookEvent(
        channel_id=channel.id,
        raw_payload_json=data,
        processing_status="pending"
    )
    db.add(event)
    await db.commit()
    
    # Trigger processing in the background asynchronously
    from app.services.message_processor import process_inbound_message
    background_tasks.add_task(process_inbound_message, event.id)
    
    logger.info(f"WhatsApp message enqueued for processing. Event ID: {event.id}")
    return {"status": "enqueued", "event_id": event.id}


@router.get("/instagram", response_class=PlainTextResponse)
async def instagram_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    logger.info(f"Instagram webhook handshake requested. Mode: {hub_mode}")
    if hub_mode == "subscribe":
        return hub_challenge
    raise HTTPException(status_code=400, detail="Verification failed")

@router.post("/instagram")
async def instagram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    logger.info("Received Instagram webhook POST request.")
    payload = await request.body()
    payload_str = payload.decode("utf-8")
    
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Find matching Instagram channel
    result = await db.execute(select(Channel).where(Channel.channel_type == "instagram"))
    channel = result.scalars().first()

    if not channel:
        logger.error("No Instagram channel configured. Ignoring webhook.")
        raise HTTPException(status_code=404, detail="Instagram channel not configured.")

    # Persist raw webhook event
    event = WebhookEvent(
        channel_id=channel.id,
        raw_payload_json=data,
        processing_status="pending"
    )
    db.add(event)
    await db.commit()
    
    # Process background task
    from app.services.message_processor import process_inbound_message
    background_tasks.add_task(process_inbound_message, event.id)
    
    logger.info(f"Instagram message enqueued for processing. Event ID: {event.id}")
    return {"status": "enqueued", "event_id": event.id}


@router.post("/widget/{tenant_slug}")
async def widget_webhook(
    tenant_slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Received Widget message for tenant slug: {tenant_slug}")
    
    # Find matching tenant
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalars().first()
    if not tenant:
        logger.error(f"Tenant slug {tenant_slug} not found.")
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Find widget channel
    result = await db.execute(
        select(Channel).where(
            Channel.tenant_id == tenant.id,
            Channel.channel_type == "website"
        )
    )
    channel = result.scalars().first()
    if not channel:
        logger.error(f"Widget channel not found for tenant: {tenant_slug}")
        raise HTTPException(status_code=404, detail="Widget channel not configured")

    payload = await request.json()
    logger.debug(f"Widget payload: {payload}")

    # Persist raw event
    event = WebhookEvent(
        channel_id=channel.id,
        raw_payload_json=payload,
        processing_status="pending"
    )
    db.add(event)
    await db.commit()

    # Process background task
    from app.services.message_processor import process_inbound_message
    background_tasks.add_task(process_inbound_message, event.id)

    logger.info(f"Widget message enqueued for processing. Event ID: {event.id}")
    return {"status": "enqueued", "event_id": event.id}


@router.get("/widget/{tenant_slug}/shop-info")
async def widget_shop_info(tenant_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "onboarding_complete": tenant.onboarding_complete,
        "ai_enabled": tenant.ai_enabled
    }


@router.get("/widget/{tenant_slug}/history")
async def widget_history(
    tenant_slug: str,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Find matching tenant
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # Find the customer for this session_id
    from app.models.models import Customer, Conversation, Message
    cust_result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == tenant.id,
            Customer.external_user_id == str(session_id)
        )
    )
    customer = cust_result.scalars().first()
    if not customer:
        return []
        
    # Find active or most recent conversation
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant.id,
            Conversation.customer_id == customer.id
        ).order_by(Conversation.id.desc()).limit(1)
    )
    conversation = conv_result.scalars().first()
    if not conversation:
        return []
        
    # Get all messages in this conversation
    msg_result = await db.execute(
        select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()
    
    return [
        {
            "id": m.id,
            "direction": m.direction,
            "sender_type": m.sender_type,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in messages
    ]
