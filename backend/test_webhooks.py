import httpx
import time
import logging
import uuid
from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import sessionmaker

# Import database session & models to verify DB state
from app.db.session import Base
from app.models.models import Tenant, Channel, Customer, Conversation, Message, WebhookEvent

from sqlalchemy.pool import NullPool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-webhooks")

BASE_URL = "http://127.0.0.1:8000"

# Synchronous connection to SQLite db for assertion checks
db_path = "../replyone.db" # Relative to backend folder
engine = create_engine(
    f"sqlite:///{db_path}", 
    poolclass=NullPool,
    connect_args={"timeout": 30.0}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    dbapi_connection.isolation_level = None
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

@event.listens_for(engine, "begin")
def do_begin(conn):
    conn.exec_driver_sql("BEGIN IMMEDIATE")

SessionLocal = sessionmaker(bind=engine)

def setup_channel_and_test():
    with httpx.Client() as client:
        # 1. Register tenant
        logger.info("Registering tenant...")
        email = f"owner_{uuid.uuid4().hex[:6]}@example.com"
        reg_payload = {
            "email": email,
            "password": "securepassword123",
            "business_name": "Ravi Boutique"
        }
        r = client.post(f"{BASE_URL}/auth/register", json=reg_payload)
        logger.info(f"Register status: {r.status_code}")
        assert r.status_code == 201
        tenant_id = r.json()["tenant_id"]

        # 2. Add WhatsApp and Widget channels in the database
        logger.info(f"Setting up channels in DB for tenant {tenant_id}...")
        session = SessionLocal()
        try:
            # Add WhatsApp Channel
            whatsapp_channel = Channel(
                tenant_id=tenant_id,
                channel_type="whatsapp",
                external_account_id="1234567890", # phone_number_id
                status="connected"
            )
            session.add(whatsapp_channel)

            # Add Website Widget Channel
            widget_channel = Channel(
                tenant_id=tenant_id,
                channel_type="website",
                status="connected"
            )
            session.add(widget_channel)
            session.commit()
            logger.info("WhatsApp and Widget channels added to DB.")
        finally:
            session.close()

        # 3. Send WhatsApp Webhook Event (Greeting - should trigger AI auto-reply)
        logger.info("Sending WhatsApp Webhook (Greeting)...")
        wa_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "12345",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "16505553333",
                                    "phone_number_id": "1234567890"
                                },
                                "contacts": [
                                    {
                                        "profile": {
                                            "name": "Parth Gupta"
                                        },
                                        "wa_id": "919999999999"
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "919999999999",
                                        "id": "wamid.HBgLOTE5OTk5OTk5OTk5FQIAERgSRjQ1QzQwQTk3RDAyMkRGNkFFAA==",
                                        "timestamp": "1650000000",
                                        "text": {
                                            "body": "Hello there!"
                                        },
                                        "type": "text"
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        r = client.post(f"{BASE_URL}/webhooks/whatsapp", json=wa_payload)
        logger.info(f"WhatsApp webhook POST status: {r.status_code}, response: {r.json()}")
        assert r.status_code == 200
        wa_event_id = r.json()["event_id"]

        # 4. Send WhatsApp Webhook Event (Complaint - should escalate)
        logger.info("Sending WhatsApp Webhook (Complaint)...")
        wa_complaint_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "12345",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "16505553333",
                                    "phone_number_id": "1234567890"
                                },
                                "contacts": [
                                    {
                                        "profile": {
                                            "name": "Parth Gupta"
                                        },
                                        "wa_id": "919999999999"
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "919999999999",
                                        "id": "wamid.HBgLOTE5OTk5OTk5OTk5FQIAERgSRjQ1QzQwQTk3RDAyMkRGNkFFAA22",
                                        "timestamp": "1650000010",
                                        "text": {
                                            "body": "This is terrible! My order is broken and I want a refund."
                                        },
                                        "type": "text"
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }
        r = client.post(f"{BASE_URL}/webhooks/whatsapp", json=wa_complaint_payload)
        logger.info(f"WhatsApp complaint webhook POST status: {r.status_code}")
        assert r.status_code == 200

        # Wait a moment for background processing task to finish
        logger.info("Waiting for background task to process messages...")
        time.sleep(4)

        # 5. Assert Database State
        session = SessionLocal()
        try:
            # Check Webhook Events
            events = session.query(WebhookEvent).all()
            for e in events:
                logger.info(f"WebhookEvent ID {e.id}: Status: {e.processing_status}, Error: {e.error_message}")
                assert e.processing_status == "processed"

            # Check Customers
            customers = session.query(Customer).all()
            logger.info(f"Customers count: {len(customers)}")
            assert len(customers) == 1
            assert customers[0].display_name == "Parth Gupta"

            # Check Conversations
            conversations = session.query(Conversation).all()
            logger.info(f"Conversations count: {len(conversations)}")
            assert len(conversations) == 1
            # The complaint should have escalated the conversation
            logger.info(f"Conversation status: {conversations[0].status}")
            assert conversations[0].status == "escalated"

            # Check Messages
            messages = session.query(Message).order_by(Message.id.asc()).all()
            logger.info(f"Messages count: {len(messages)}")
            # Expected messages:
            # 1. Inbound greeting
            # 2. Outbound AI reply (auto-reply greeting)
            # 3. Inbound complaint
            for m in messages:
                logger.info(f"Message ID {m.id}: Direction: {m.direction}, Sender: {m.sender_type}, Content: '{m.content}'")
            
            assert len(messages) == 3
            assert messages[0].sender_type == "customer"
            assert messages[1].sender_type == "ai"
            assert messages[2].sender_type == "customer"

            logger.info("ALL WEBHOOK & MESSAGE PROCESSING PIPELINE TESTS PASSED!")

        finally:
            session.close()

if __name__ == "__main__":
    setup_channel_and_test()
