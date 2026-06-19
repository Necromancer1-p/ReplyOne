import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-api")

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    with httpx.Client() as client:
        # 1. Healthcheck
        logger.info("Testing healthcheck...")
        r = client.get(f"{BASE_URL}/health")
        logger.info(f"Healthcheck status: {r.status_code}, response: {r.json()}")
        assert r.status_code == 200

        # 2. Register a new tenant & owner
        logger.info("Testing registration...")
        payload = {
            "email": "owner@example.com",
            "password": "securepassword123",
            "business_name": "Ravi Clothing Boutique"
        }
        r = client.post(f"{BASE_URL}/auth/register", json=payload)
        logger.info(f"Register status: {r.status_code}, response: {r.json()}")
        assert r.status_code == 201
        data = r.json()
        access_token = data["access_token"]
        assert data["role"] == "owner"
        assert data["onboarding_complete"] is False

        # 3. Test duplicate registration (should fail with 409)
        logger.info("Testing duplicate registration...")
        r = client.post(f"{BASE_URL}/auth/register", json=payload)
        logger.info(f"Duplicate Register status: {r.status_code}, response: {r.json()}")
        assert r.status_code == 409

        # 4. Login
        logger.info("Testing login...")
        login_payload = {
            "email": "owner@example.com",
            "password": "securepassword123"
        }
        r = client.post(f"{BASE_URL}/auth/login", json=login_payload)
        logger.info(f"Login status: {r.status_code}, response: {r.json()}")
        assert r.status_code == 200

        # 5. Token refresh
        logger.info("Testing refresh token...")
        r = client.post(f"{BASE_URL}/auth/refresh")
        logger.info(f"Refresh status: {r.status_code}, response: {r.json()}")
        assert r.status_code == 200

        # 6. Logout
        logger.info("Testing logout...")
        r = client.post(f"{BASE_URL}/auth/logout")
        logger.info(f"Logout status: {r.status_code}, response: {r.json()}")
        assert r.status_code == 200

        logger.info("ALL AUTH FLOW TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_flow()
