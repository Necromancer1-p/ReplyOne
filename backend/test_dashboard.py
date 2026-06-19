import httpx
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Import database session & models to verify DB state
from app.db.session import Base
from app.models.models import Tenant, Channel, Customer, Conversation, Message, ShopSettings, KnowledgeBaseEntry, Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-dashboard")

BASE_URL = "http://127.0.0.1:8000"

def test_dashboard_flow():
    with httpx.Client() as client:
        # 1. Register a tenant & owner
        logger.info("Registering owner...")
        reg_payload = {
            "email": "dashboard_test@example.com",
            "password": "securepassword123",
            "business_name": "Test Dashboard Corp"
        }
        r = client.post(f"{BASE_URL}/auth/register", json=reg_payload)
        logger.info(f"Register status: {r.status_code}")
        assert r.status_code == 201
        
        data = r.json()
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get Settings
        logger.info("Testing GET /dashboard/settings...")
        r = client.get(f"{BASE_URL}/dashboard/settings", headers=headers)
        logger.info(f"GET settings response: {r.json()}")
        assert r.status_code == 200
        assert r.json()["ai_tone"] == "balanced"
        
        # 3. Update Settings
        logger.info("Testing PUT /dashboard/settings...")
        settings_payload = {
            "ai_tone": "friendly",
            "ai_confidence_threshold": 0.85
        }
        r = client.put(f"{BASE_URL}/dashboard/settings", json=settings_payload, headers=headers)
        logger.info(f"PUT settings response: {r.json()}")
        assert r.status_code == 200
        assert r.json()["ai_tone"] == "friendly"
        assert r.json()["ai_confidence_threshold"] == 0.85

        # 4. Create FAQ
        logger.info("Testing POST /dashboard/knowledge-base...")
        faq_payload = {
            "category": "shipping",
            "question": "How long does shipping take?",
            "content": "Shipping takes 3-5 business days."
        }
        r = client.post(f"{BASE_URL}/dashboard/knowledge-base", json=faq_payload, headers=headers)
        logger.info(f"POST FAQ response: {r.json()}")
        assert r.status_code == 200
        faq_id = r.json()["id"]
        
        # 5. List FAQs
        logger.info("Testing GET /dashboard/knowledge-base...")
        r = client.get(f"{BASE_URL}/dashboard/knowledge-base", headers=headers)
        logger.info(f"GET FAQ response: {r.json()}")
        assert r.status_code == 200
        assert len(r.json()) >= 1
        
        # 6. Create Product
        logger.info("Testing POST /dashboard/products...")
        prod_payload = {
            "name": "Leather Wallet",
            "price": 1299.00,
            "currency": "INR",
            "stock_status": "in_stock",
            "description": "Premium genuine leather wallet."
        }
        r = client.post(f"{BASE_URL}/dashboard/products", json=prod_payload, headers=headers)
        logger.info(f"POST Product response: {r.json()}")
        assert r.status_code == 200
        prod_id = r.json()["id"]
        
        # 7. List Products
        logger.info("Testing GET /dashboard/products...")
        r = client.get(f"{BASE_URL}/dashboard/products", headers=headers)
        logger.info(f"GET Products response: {r.json()}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

        # 8. Complete Onboarding
        logger.info("Testing POST /dashboard/onboarding/complete...")
        r = client.post(f"{BASE_URL}/dashboard/onboarding/complete", headers=headers)
        logger.info(f"Complete Onboarding status: {r.status_code}")
        assert r.status_code == 200
        
        # 9. Get Channels
        logger.info("Testing GET /dashboard/channels...")
        r = client.get(f"{BASE_URL}/dashboard/channels", headers=headers)
        logger.info(f"GET channels response: {r.json()}")
        assert r.status_code == 200
        
        # 10. Add mock Channel
        logger.info("Testing POST /dashboard/channels...")
        chan_payload = {
            "channel_type": "website",
            "widget_config_json": {"color": "#6366F1"}
        }
        r = client.post(f"{BASE_URL}/dashboard/channels", json=chan_payload, headers=headers)
        logger.info(f"POST channel response: {r.json()}")
        assert r.status_code == 200
        
        # 11. Get Analytics
        logger.info("Testing GET /dashboard/analytics...")
        r = client.get(f"{BASE_URL}/dashboard/analytics", headers=headers)
        logger.info(f"GET analytics response: {r.json()}")
        assert r.status_code == 200
        
        logger.info("ALL DASHBOARD ENDPOINT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_dashboard_flow()
