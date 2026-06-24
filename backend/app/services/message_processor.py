import logging
import datetime
import os
import json
import httpx
import asyncio
from sqlalchemy.future import select

from app.db.session import AsyncSessionLocal, tenant_context
from app.models.models import (
    Tenant, Channel, Customer, Conversation, Message,
    AIResponseLog, WebhookEvent, ShopSettings, KnowledgeBaseEntry, Product
)

logger = logging.getLogger("replyone.processor")

# Global async lock to serialize database writes for SQLite compatibility
db_write_lock = asyncio.Lock()

async def process_inbound_message(event_id: int):
    """Processes an enqueued inbound webhook event."""
    await db_write_lock.acquire()
    try:
        await _process_inbound_message_impl(event_id)
    finally:
        db_write_lock.release()

async def _process_inbound_message_impl(event_id: int):
    logger.info(f"Background task: starting processing for webhook event ID: {event_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch the webhook event
            result = await db.execute(select(WebhookEvent).where(WebhookEvent.id == event_id))
            event = result.scalars().first()
            if not event:
                logger.error(f"Webhook event ID {event_id} not found in database.")
                return

            # Fetch channel context
            result = await db.execute(select(Channel).where(Channel.id == event.channel_id))
            channel = result.scalars().first()
            if not channel:
                logger.error(f"Channel ID {event.channel_id} not found for event {event_id}")
                event.processing_status = "failed"
                event.error_message = "Channel not found"
                await db.commit()
                return

            # Set tenant context for this thread execution
            tenant_id = channel.tenant_id
            tenant_context.set(tenant_id)
            logger.info(f"Processing webhook for Tenant ID: {tenant_id}, Channel ID: {channel.id} ({channel.channel_type})")

            # Fetch tenant settings
            result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = result.scalars().first()
            if not tenant:
                logger.error(f"Tenant ID {tenant_id} not found.")
                event.processing_status = "failed"
                event.error_message = "Tenant not found"
                await db.commit()
                return

            # Fetch settings
            result = await db.execute(select(ShopSettings).where(ShopSettings.tenant_id == tenant_id))
            settings = result.scalars().first()
            
            payload = event.raw_payload_json
            
            # 2. Normalise Platform Payload
            external_user_id = None
            display_name = None
            content = ""
            attachment_url = None
            external_message_id = None

            if channel.channel_type == "whatsapp":
                logger.debug("Normalising WhatsApp payload...")
                try:
                    message_data = payload["entry"][0]["changes"][0]["value"]["messages"][0]
                    external_user_id = message_data["from"]
                    external_message_id = message_data["id"]
                    
                    profile_data = payload["entry"][0]["changes"][0]["value"]["contacts"][0]
                    display_name = profile_data.get("profile", {}).get("name", "WhatsApp Customer")
                    
                    if message_data.get("type") == "text":
                        content = message_data["text"]["body"]
                    else:
                        content = f"[Received {message_data.get('type')} message]"
                except Exception as e:
                    logger.warning(f"Error parsing WhatsApp payload structure: {e}")
                    content = "[Inbound Message]"

            elif channel.channel_type == "instagram":
                logger.debug("Normalising Instagram payload...")
                try:
                    messaging = payload["entry"][0]["messaging"][0]
                    external_user_id = messaging["sender"]["id"]
                    external_message_id = messaging["message"]["mid"]
                    content = messaging["message"].get("text", "")
                    display_name = "Instagram User"
                except Exception as e:
                    logger.warning(f"Error parsing Instagram payload: {e}")
                    content = "[Inbound DM]"

            elif channel.channel_type == "website":
                logger.debug("Normalising Website Widget payload...")
                try:
                    external_user_id = payload.get("external_user_id")
                    display_name = payload.get("display_name", "Web Customer")
                    content = payload.get("content", "")
                except Exception as e:
                    logger.warning(f"Error parsing Widget payload: {e}")
                    content = "[Inbound Web Chat]"

            # Validate extraction
            if not external_user_id:
                logger.error("Could not parse external_user_id from webhook payload.")
                event.processing_status = "failed"
                event.error_message = "Missing external_user_id"
                await db.commit()
                return

            logger.info(f"Normalised message. Customer: {display_name} ({external_user_id}), Content: '{content}'")

            # 3. Upsert Customer Profile
            customer = None
            try:
                async with db.begin_nested():
                    result = await db.execute(
                        select(Customer).where(
                            Customer.tenant_id == tenant_id,
                            Customer.channel_id == channel.id,
                            Customer.external_user_id == str(external_user_id)
                        )
                    )
                    customer = result.scalars().first()
                    if not customer:
                        logger.info(f"Creating new customer profile for external ID: {external_user_id}")
                        customer = Customer(
                            tenant_id=tenant_id,
                            channel_id=channel.id,
                            external_user_id=str(external_user_id),
                            display_name=display_name,
                            phone=str(external_user_id) if channel.channel_type == "whatsapp" else None
                        )
                        db.add(customer)
                        await db.flush()
                    else:
                        customer.last_seen_at = datetime.datetime.utcnow()
                        if display_name and (customer.display_name == "WhatsApp Customer" or customer.display_name == "Instagram User"):
                            customer.display_name = display_name
                        db.add(customer)
                        logger.debug(f"Updated existing customer ID: {customer.id}")
            except Exception as e:
                logger.warning(f"Concurrent customer write race detected: {e}. Fetching existing customer profile...")
                result = await db.execute(
                    select(Customer).where(
                        Customer.tenant_id == tenant_id,
                        Customer.channel_id == channel.id,
                        Customer.external_user_id == str(external_user_id)
                    )
                )
                customer = result.scalars().first()
                if not customer:
                    logger.error("Failed to recover customer profile after database savepoint rollback.")
                    raise e

            # 4. Fetch or Create Conversation
            conversation = None
            try:
                async with db.begin_nested():
                    # An active conversation has status open, pending, or escalated
                    result = await db.execute(
                        select(Conversation).where(
                            Conversation.tenant_id == tenant_id,
                            Conversation.customer_id == customer.id,
                            Conversation.status.in_(["open", "pending", "escalated"])
                        )
                    )
                    conversation = result.scalars().first()
                    if not conversation:
                        logger.info(f"No active conversation. Creating new thread for customer ID: {customer.id}")
                        conversation = Conversation(
                            tenant_id=tenant_id,
                            customer_id=customer.id,
                            channel_id=channel.id,
                            channel=channel.channel_type if channel.channel_type != "website" else "widget",
                            status="open",
                            ai_active=tenant.ai_enabled
                        )
                        db.add(conversation)
                        await db.flush()
                    else:
                        conversation.last_message_at = datetime.datetime.utcnow()
                        db.add(conversation)
                        logger.debug(f"Adding message to active conversation ID: {conversation.id}")
            except Exception as e:
                logger.warning(f"Concurrent conversation write race detected: {e}. Fetching existing conversation...")
                result = await db.execute(
                    select(Conversation).where(
                        Conversation.tenant_id == tenant_id,
                        Conversation.customer_id == customer.id,
                        Conversation.status.in_(["open", "pending", "escalated"])
                    )
                )
                conversation = result.scalars().first()
                if not conversation:
                    logger.error("Failed to recover conversation after savepoint rollback.")
                    raise e

            # 5. Persist Inbound Message
            message = Message(
                tenant_id=tenant_id,
                conversation_id=conversation.id,
                direction="inbound",
                sender_type="customer",
                content=content,
                external_message_id=external_message_id,
                delivery_status="read"
            )
            db.add(message)
            await db.flush()
            logger.info(f"Saved message ID {message.id} to conversation {conversation.id}")

            # Publish event to WebSocket clients
            from app.core.websocket import publish_websocket_event
            msg_data = {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "direction": message.direction,
                "sender_type": message.sender_type,
                "sender_user_id": message.sender_user_id,
                "content": message.content,
                "attachment_url": message.attachment_url,
                "external_message_id": message.external_message_id,
                "delivery_status": message.delivery_status,
                "created_at": message.created_at.isoformat() if message.created_at else None,
                "customer_session_id": customer.external_user_id
            }
            await publish_websocket_event(tenant_id, "message_created", msg_data)

            # Construct conversation update payload matching ConversationResponse
            conv_data = {
                "id": conversation.id,
                "customer_id": conversation.customer_id,
                "channel_id": conversation.channel_id,
                "channel": conversation.channel,
                "status": conversation.status,
                "assigned_agent_id": conversation.assigned_agent_id,
                "ai_active": conversation.ai_active,
                "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "customer": {
                    "id": customer.id,
                    "display_name": customer.display_name,
                    "avatar_url": customer.avatar_url,
                    "phone": customer.phone,
                    "external_user_id": customer.external_user_id
                },
                "last_message": message.content
            }
            await publish_websocket_event(tenant_id, "conversation_updated", conv_data)

            # 6. Evaluate AI Logic & Call AI Inference
            # We only execute AI if AI is enabled globally for tenant AND active on conversation thread
            if tenant.ai_enabled and conversation.ai_active:
                logger.info(f"AI is active. Calling AI inference for message ID: {message.id}")
                await trigger_ai_response(db, tenant_id, conversation, message, settings)
            else:
                logger.info(f"AI skipped. Tenant AI enabled: {tenant.ai_enabled}, Conversation AI active: {conversation.ai_active}")
                # Mark conversation status as pending human response
                conversation.status = "pending"
                db.add(conversation)

            # Mark webhook event as processed successfully
            event.processing_status = "processed"
            db.add(event)
            
            await db.commit()
            logger.info(f"Webhook event ID {event_id} processed successfully.")

        except Exception as e:
            logger.error(f"Error processing webhook event {event_id}: {e}", exc_info=True)
            await db.rollback()
            try:
                event.processing_status = "failed"
                event.error_message = str(e)
                db.add(event)
                await db.commit()
            except Exception as commit_err:
                logger.error(f"Failed to write error state for event {event_id}: {commit_err}")


async def query_gemini_model(model_name: str, api_key: str, prompt: str, user_message: str, tone: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    system_instruction_text = (
        "You are an AI customer support assistant. Analyze the user message based on the provided business context and return a structured JSON response. "
        "You must identify the user's intent and draft a suggested reply matching the configured tone.\n\n"
        f"Business Context:\n{prompt}\n\n"
        f"Configured Tone: {tone}"
    )
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": user_message
                    }
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {
                    "text": system_instruction_text
                }
            ]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "intent": {
                        "type": "STRING",
                        "description": "The classified intent of the user message (e.g., greeting, complaint, order_status, return_request, price_inquiry, availability, compliment, general_inquiry)."
                    },
                    "confidence": {
                        "type": "NUMBER",
                        "description": "Confidence score of the intent classification from 0.0 to 1.0."
                    },
                    "suggested_reply": {
                        "type": "STRING",
                        "description": "The drafted auto-reply to the customer using the knowledge base and product catalogue context, matching the configured tone."
                    }
                },
                "required": ["intent", "confidence", "suggested_reply"]
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15.0
        )
        
    if resp.status_code == 200:
        resp_json = resp.json()
        try:
            text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as parse_err:
            logger.error(f"Error parsing Gemini response content for {model_name}: {parse_err}, Response: {resp_json}")
            raise Exception("Invalid Gemini response structure")
    else:
        logger.error(f"Gemini API returned error for model {model_name}: {resp.status_code} - {resp.text}")
        raise Exception(f"Gemini API error {resp.status_code}")

async def trigger_ai_response(
    db: AsyncSessionLocal, 
    tenant_id: int, 
    conversation: Conversation, 
    inbound_message: Message,
    settings: ShopSettings
):
    """Triggers real Gemini AI response logic with multi-model failover."""
    logger.info(f"Triggering Gemini AI response for conversation {conversation.id}")
    
    # Construct System Prompt by gathering FAQ and Product details
    faq_text = ""
    result = await db.execute(select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.tenant_id == tenant_id, KnowledgeBaseEntry.is_active == True))
    faqs = result.scalars().all()
    for f in faqs:
        faq_text += f"Q: {f.question}\nA: {f.content}\n\n"
        
    prod_text = ""
    result = await db.execute(select(Product).where(Product.tenant_id == tenant_id, Product.is_active == True))
    prods = result.scalars().all()
    for p in prods:
        prod_text += f"Product: {p.name}, Price: {p.price} {p.currency}, Available: {p.stock_status}\n"
        
    system_prompt = f"Knowledge base FAQs:\n{faq_text}\nProduct catalogue:\n{prod_text}\n"
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    tone = settings.ai_tone if settings else "balanced"
    
    ai_data = None
    resolved_model = None
    
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY environment variable is not configured. Directing message to human agent queue.")
    else:
        # 1. Attempt Primary model: gemini-2.5-flash
        try:
            logger.info("Attempting primary LLM model: gemini-2.5-flash")
            ai_data = await query_gemini_model("gemini-2.5-flash", gemini_api_key, system_prompt, inbound_message.content, tone)
            resolved_model = "gemini-2.5-flash"
        except Exception as e_primary:
            logger.warning(f"Primary model gemini-2.5-flash failed: {e_primary}. Attempting failover to secondary model...")
            # 2. Attempt Fallback model: gemini-1.5-flash
            try:
                ai_data = await query_gemini_model("gemini-1.5-flash", gemini_api_key, system_prompt, inbound_message.content, tone)
                resolved_model = "gemini-1.5-flash"
                logger.info("Failover succeeded with secondary LLM model: gemini-1.5-flash")
            except Exception as e_secondary:
                logger.critical(f"All LLM models failed. Primary error: {e_primary}, Secondary error: {e_secondary}")
                ai_data = None
                
    if ai_data:
        try:
            intent = ai_data["intent"]
            confidence = float(ai_data["confidence"])
            suggested_reply = ai_data["suggested_reply"]
            logger.info(f"AI response received. Model: {resolved_model}, Intent: {intent}, Confidence: {confidence}")
            
            # Log AI transaction
            ai_log = AIResponseLog(
                tenant_id=tenant_id,
                message_id=inbound_message.id,
                intent_classified=intent,
                sentiment="neutral" if intent != "complaint" else "urgent",
                confidence_score=confidence,
                model_name=resolved_model,
                latency_ms=150
            )
            db.add(ai_log)
            
            # Decide: Auto-reply or Escalate
            threshold = float(settings.ai_confidence_threshold) if settings else 0.700
            should_auto_reply = (confidence >= threshold) and (intent != "complaint")
            
            if should_auto_reply:
                logger.info(f"Auto-reply conditions met (Confidence {confidence} >= Threshold {threshold}). Sending response...")
                # Create outbound message
                outbound = Message(
                    tenant_id=tenant_id,
                    conversation_id=conversation.id,
                    direction="outbound",
                    sender_type="ai",
                    content=suggested_reply,
                    delivery_status="sent"
                )
                db.add(outbound)
                await db.flush()
                
                # Mock platform API send call
                logger.info(f"Outbound API call mock: Sent '{suggested_reply}' to platform endpoint.")

                # Publish event to WebSocket clients
                from app.core.websocket import publish_websocket_event
                from app.models.models import Customer
                
                cust_result = await db.execute(select(Customer).where(Customer.id == conversation.customer_id))
                customer = cust_result.scalars().first()

                outbound_data = {
                    "id": outbound.id,
                    "conversation_id": outbound.conversation_id,
                    "direction": outbound.direction,
                    "sender_type": outbound.sender_type,
                    "sender_user_id": outbound.sender_user_id,
                    "content": outbound.content,
                    "attachment_url": outbound.attachment_url,
                    "external_message_id": outbound.external_message_id,
                    "delivery_status": outbound.delivery_status,
                    "created_at": outbound.created_at.isoformat() if outbound.created_at else None,
                    "customer_session_id": customer.external_user_id if customer else None
                }
                await publish_websocket_event(tenant_id, "message_created", outbound_data)

                cust_data = {
                    "id": customer.id,
                    "display_name": customer.display_name,
                    "avatar_url": customer.avatar_url,
                    "phone": customer.phone,
                    "external_user_id": customer.external_user_id
                } if customer else None

                conv_data = {
                    "id": conversation.id,
                    "customer_id": conversation.customer_id,
                    "channel_id": conversation.channel_id,
                    "channel": conversation.channel,
                    "status": conversation.status,
                    "assigned_agent_id": conversation.assigned_agent_id,
                    "ai_active": conversation.ai_active,
                    "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                    "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                    "customer": cust_data,
                    "last_message": outbound.content
                }
                await publish_websocket_event(tenant_id, "conversation_updated", conv_data)

            else:
                logger.info(f"Auto-reply conditions not met. Escalating to human queue. Intent: {intent}")
                conversation.status = "escalated" if intent == "complaint" else "pending"
                db.add(conversation)
                await db.flush()

                # Publish conversation update
                from app.core.websocket import publish_websocket_event
                from app.models.models import Customer
                cust_result = await db.execute(select(Customer).where(Customer.id == conversation.customer_id))
                customer = cust_result.scalars().first()
                cust_data = {
                    "id": customer.id,
                    "display_name": customer.display_name,
                    "avatar_url": customer.avatar_url,
                    "phone": customer.phone,
                    "external_user_id": customer.external_user_id
                } if customer else None

                conv_data = {
                    "id": conversation.id,
                    "customer_id": conversation.customer_id,
                    "channel_id": conversation.channel_id,
                    "channel": conversation.channel,
                    "status": conversation.status,
                    "assigned_agent_id": conversation.assigned_agent_id,
                    "ai_active": conversation.ai_active,
                    "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                    "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                    "customer": cust_data,
                    "last_message": inbound_message.content
                }
                await publish_websocket_event(tenant_id, "conversation_updated", conv_data)
        except Exception as handler_err:
            logger.error(f"Error handling Gemini LLM response payload: {handler_err}", exc_info=True)
            conversation.status = "pending"
            db.add(conversation)
    else:
        # Failover to human takeover directly (no mock-ai fallback)
        logger.warning("No LLM response obtained. Defaulting conversation to pending human takeover.")
        conversation.status = "pending"
        db.add(conversation)
