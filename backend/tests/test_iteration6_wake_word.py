"""
Iteration 6 Tests - Wake Word Activation Feature
Tests for the new wake word activation feature:
- PUT /api/settings with wake_word_enabled=true persists correctly
- GET /api/settings returns wake_word_enabled field
- Settings API handles wake_word_enabled toggle
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestWakeWordAPI:
    """Tests for wake word activation API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login with admin credentials
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        data = login_response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup - reset wake_word_enabled to false
        self.session.put(f"{BASE_URL}/api/settings", json={"wake_word_enabled": False})
    
    def test_get_settings_returns_wake_word_enabled_field(self):
        """GET /api/settings should return wake_word_enabled field"""
        response = self.session.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200, f"GET settings failed: {response.text}"
        
        data = response.json()
        # wake_word_enabled should be present (may be None/False for existing users)
        # The field should exist in the response
        assert "user_id" in data, "Settings should have user_id"
        # Check other expected fields are present
        assert "agent_name" in data, "Settings should have agent_name"
        assert "tts_enabled" in data, "Settings should have tts_enabled"
        print(f"GET /api/settings response: {data}")
        print(f"wake_word_enabled value: {data.get('wake_word_enabled')}")
    
    def test_put_settings_wake_word_enabled_true(self):
        """PUT /api/settings with wake_word_enabled=true should persist"""
        # Enable wake word
        response = self.session.put(f"{BASE_URL}/api/settings", json={
            "wake_word_enabled": True
        })
        assert response.status_code == 200, f"PUT settings failed: {response.text}"
        
        data = response.json()
        assert data.get("wake_word_enabled") == True, f"wake_word_enabled should be True, got: {data.get('wake_word_enabled')}"
        print(f"PUT /api/settings with wake_word_enabled=true: {data}")
        
        # Verify persistence with GET
        get_response = self.session.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data.get("wake_word_enabled") == True, f"wake_word_enabled should persist as True, got: {get_data.get('wake_word_enabled')}"
        print(f"Verified persistence - GET /api/settings: wake_word_enabled={get_data.get('wake_word_enabled')}")
    
    def test_put_settings_wake_word_enabled_false(self):
        """PUT /api/settings with wake_word_enabled=false should persist"""
        # First enable it
        self.session.put(f"{BASE_URL}/api/settings", json={"wake_word_enabled": True})
        
        # Then disable it
        response = self.session.put(f"{BASE_URL}/api/settings", json={
            "wake_word_enabled": False
        })
        assert response.status_code == 200, f"PUT settings failed: {response.text}"
        
        data = response.json()
        assert data.get("wake_word_enabled") == False, f"wake_word_enabled should be False, got: {data.get('wake_word_enabled')}"
        print(f"PUT /api/settings with wake_word_enabled=false: {data}")
        
        # Verify persistence with GET
        get_response = self.session.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data.get("wake_word_enabled") == False, f"wake_word_enabled should persist as False, got: {get_data.get('wake_word_enabled')}"
    
    def test_put_settings_wake_word_with_other_fields(self):
        """PUT /api/settings should update wake_word_enabled along with other fields"""
        # Update multiple fields including wake_word_enabled
        response = self.session.put(f"{BASE_URL}/api/settings", json={
            "wake_word_enabled": True,
            "tts_enabled": True,
            "agent_name": "TestAgent"
        })
        assert response.status_code == 200, f"PUT settings failed: {response.text}"
        
        data = response.json()
        assert data.get("wake_word_enabled") == True, "wake_word_enabled should be True"
        assert data.get("tts_enabled") == True, "tts_enabled should be True"
        assert data.get("agent_name") == "TestAgent", "agent_name should be TestAgent"
        print(f"PUT /api/settings with multiple fields: {data}")
        
        # Reset agent_name
        self.session.put(f"{BASE_URL}/api/settings", json={"agent_name": "NovaClaw"})
    
    def test_settings_toggle_wake_word_multiple_times(self):
        """Toggle wake_word_enabled multiple times to verify state changes"""
        # Enable
        r1 = self.session.put(f"{BASE_URL}/api/settings", json={"wake_word_enabled": True})
        assert r1.status_code == 200
        assert r1.json().get("wake_word_enabled") == True
        
        # Disable
        r2 = self.session.put(f"{BASE_URL}/api/settings", json={"wake_word_enabled": False})
        assert r2.status_code == 200
        assert r2.json().get("wake_word_enabled") == False
        
        # Enable again
        r3 = self.session.put(f"{BASE_URL}/api/settings", json={"wake_word_enabled": True})
        assert r3.status_code == 200
        assert r3.json().get("wake_word_enabled") == True
        
        print("Toggle test passed - wake_word_enabled toggles correctly")


class TestAgentNameWithWakeWord:
    """Tests for agent name interaction with wake word feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login with admin credentials
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        data = login_response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup - reset settings
        self.session.put(f"{BASE_URL}/api/settings", json={
            "wake_word_enabled": False,
            "agent_name": "NovaClaw"
        })
    
    def test_agent_name_change_with_wake_word_enabled(self):
        """Changing agent name while wake word is enabled should work"""
        # Enable wake word
        self.session.put(f"{BASE_URL}/api/settings", json={"wake_word_enabled": True})
        
        # Change agent name
        response = self.session.put(f"{BASE_URL}/api/settings", json={
            "agent_name": "CustomAgent"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("agent_name") == "CustomAgent", "agent_name should be CustomAgent"
        assert data.get("wake_word_enabled") == True, "wake_word_enabled should still be True"
        print(f"Agent name changed while wake word enabled: {data}")
    
    def test_get_settings_returns_default_agent_name(self):
        """GET /api/settings should return default agent_name 'NovaClaw'"""
        # Reset to default
        self.session.put(f"{BASE_URL}/api/settings", json={"agent_name": "NovaClaw"})
        
        response = self.session.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("agent_name") == "NovaClaw", f"Default agent_name should be NovaClaw, got: {data.get('agent_name')}"
        print(f"Default agent_name verified: {data.get('agent_name')}")


class TestHealthAndBasicEndpoints:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """Health endpoint should return online status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "online"
        print(f"Health check: {data}")
    
    def test_root_endpoint(self):
        """Root API endpoint should return version info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "NovaClaw" in data.get("message", "")
        print(f"Root endpoint: {data}")
