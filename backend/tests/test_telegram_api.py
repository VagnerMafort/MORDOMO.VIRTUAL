"""
Test Telegram Integration API - Iteration 3
Tests for:
- POST /api/telegram/connect - Connect a Telegram bot (expects 400 with invalid token)
- GET /api/telegram/status - Get connection status (initially false)
- POST /api/telegram/disconnect - Disconnect bot
- POST /api/telegram/webhook/{user_id} - Webhook endpoint (no auth required)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTelegramAPI:
    """Telegram Integration API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        data = login_response.json()
        self.token = data.get("access_token")
        self.user_id = data.get("user", {}).get("id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup - disconnect any telegram connection
        try:
            self.session.post(f"{BASE_URL}/api/telegram/disconnect")
        except:
            pass
    
    # ─── Telegram Status Tests ───────────────────────────────────────────────
    def test_telegram_status_initial(self):
        """GET /api/telegram/status - Should return connected:false initially"""
        response = self.session.get(f"{BASE_URL}/api/telegram/status")
        
        assert response.status_code == 200, f"Status check failed: {response.text}"
        
        data = response.json()
        assert "connected" in data, "Response should have 'connected' field"
        # Initially should be false (or could be true if previously connected)
        assert isinstance(data["connected"], bool), "'connected' should be boolean"
        print(f"Telegram status: connected={data['connected']}")
    
    def test_telegram_status_requires_auth(self):
        """GET /api/telegram/status - Should require authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/telegram/status")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    # ─── Telegram Connect Tests ──────────────────────────────────────────────
    def test_telegram_connect_invalid_token(self):
        """POST /api/telegram/connect - Should return 400 with invalid token"""
        response = self.session.post(f"{BASE_URL}/api/telegram/connect", json={
            "bot_token": "invalid_token_12345"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Response should have 'detail' field"
        # Should contain error message about invalid token
        assert "invalido" in data["detail"].lower() or "invalid" in data["detail"].lower(), \
            f"Error message should mention invalid token: {data['detail']}"
        print(f"Connect with invalid token error: {data['detail']}")
    
    def test_telegram_connect_empty_token(self):
        """POST /api/telegram/connect - Should handle empty token"""
        response = self.session.post(f"{BASE_URL}/api/telegram/connect", json={
            "bot_token": ""
        })
        
        # Should return 400 or 422 for empty token
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
    
    def test_telegram_connect_requires_auth(self):
        """POST /api/telegram/connect - Should require authentication"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.post(f"{BASE_URL}/api/telegram/connect", json={
            "bot_token": "test_token"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_telegram_connect_missing_token_field(self):
        """POST /api/telegram/connect - Should require bot_token field"""
        response = self.session.post(f"{BASE_URL}/api/telegram/connect", json={})
        
        # Should return 422 for missing required field
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    # ─── Telegram Disconnect Tests ───────────────────────────────────────────
    def test_telegram_disconnect(self):
        """POST /api/telegram/disconnect - Should disconnect bot"""
        response = self.session.post(f"{BASE_URL}/api/telegram/disconnect")
        
        assert response.status_code == 200, f"Disconnect failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have 'message' field"
        print(f"Disconnect response: {data['message']}")
        
        # Verify status is now disconnected
        status_response = self.session.get(f"{BASE_URL}/api/telegram/status")
        status_data = status_response.json()
        assert status_data["connected"] == False, "Should be disconnected after disconnect call"
    
    def test_telegram_disconnect_requires_auth(self):
        """POST /api/telegram/disconnect - Should require authentication"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.post(f"{BASE_URL}/api/telegram/disconnect")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    # ─── Telegram Webhook Tests ──────────────────────────────────────────────
    def test_telegram_webhook_no_auth_required(self):
        """POST /api/telegram/webhook/{user_id} - Should NOT require auth (Telegram calls it)"""
        # Create session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        # Send a mock Telegram update
        mock_update = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 12345, "first_name": "Test"},
                "chat": {"id": 12345, "type": "private"},
                "date": 1234567890,
                "text": "Hello test"
            }
        }
        
        response = no_auth_session.post(
            f"{BASE_URL}/api/telegram/webhook/{self.user_id}",
            json=mock_update
        )
        
        # Should return 200 OK (even if no bot connected, it should handle gracefully)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ok") == True, "Webhook should return ok:true"
        print(f"Webhook response: {data}")
    
    def test_telegram_webhook_empty_message(self):
        """POST /api/telegram/webhook/{user_id} - Should handle empty message gracefully"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        # Send update without text
        mock_update = {
            "update_id": 123456790,
            "message": {
                "message_id": 2,
                "from": {"id": 12345, "first_name": "Test"},
                "chat": {"id": 12345, "type": "private"},
                "date": 1234567890
                # No text field
            }
        }
        
        response = no_auth_session.post(
            f"{BASE_URL}/api/telegram/webhook/{self.user_id}",
            json=mock_update
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json().get("ok") == True
    
    def test_telegram_webhook_start_command(self):
        """POST /api/telegram/webhook/{user_id} - Should handle /start command"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        mock_update = {
            "update_id": 123456791,
            "message": {
                "message_id": 3,
                "from": {"id": 12345, "first_name": "Test"},
                "chat": {"id": 12345, "type": "private"},
                "date": 1234567890,
                "text": "/start"
            }
        }
        
        response = no_auth_session.post(
            f"{BASE_URL}/api/telegram/webhook/{self.user_id}",
            json=mock_update
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json().get("ok") == True
    
    def test_telegram_webhook_invalid_user_id(self):
        """POST /api/telegram/webhook/{user_id} - Should handle invalid user_id gracefully"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        mock_update = {
            "update_id": 123456792,
            "message": {
                "message_id": 4,
                "from": {"id": 12345, "first_name": "Test"},
                "chat": {"id": 12345, "type": "private"},
                "date": 1234567890,
                "text": "Hello"
            }
        }
        
        response = no_auth_session.post(
            f"{BASE_URL}/api/telegram/webhook/invalid_user_id_12345",
            json=mock_update
        )
        
        # Should still return 200 OK (graceful handling)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestTelegramIntegrationFlow:
    """End-to-end flow tests for Telegram integration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        
        data = login_response.json()
        self.token = data.get("access_token")
        self.user_id = data.get("user", {}).get("id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup
        try:
            self.session.post(f"{BASE_URL}/api/telegram/disconnect")
        except:
            pass
    
    def test_full_telegram_flow(self):
        """Test complete flow: check status -> try connect -> disconnect"""
        # 1. Check initial status
        status_response = self.session.get(f"{BASE_URL}/api/telegram/status")
        assert status_response.status_code == 200
        initial_status = status_response.json()
        print(f"Initial status: {initial_status}")
        
        # 2. Try to connect with invalid token (should fail with 400)
        connect_response = self.session.post(f"{BASE_URL}/api/telegram/connect", json={
            "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        })
        assert connect_response.status_code == 400, "Invalid token should return 400"
        error = connect_response.json()
        print(f"Connect error (expected): {error.get('detail')}")
        
        # 3. Disconnect (should work even if not connected)
        disconnect_response = self.session.post(f"{BASE_URL}/api/telegram/disconnect")
        assert disconnect_response.status_code == 200
        
        # 4. Verify disconnected status
        final_status = self.session.get(f"{BASE_URL}/api/telegram/status")
        assert final_status.status_code == 200
        assert final_status.json()["connected"] == False
        print("Full Telegram flow test passed!")
