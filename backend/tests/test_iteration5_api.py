"""
Iteration 5 API Tests - Hands-Free Mode & Agent Personality Customization
Tests:
1. Settings API - agent_name and agent_personality fields
2. GET /api/settings returns agent_name and agent_personality
3. PUT /api/settings updates agent_name and agent_personality
4. Conversation creation with [Voz] prefix (for hands-free mode)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSettingsAgentIdentity:
    """Test agent_name and agent_personality fields in settings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login with admin credentials
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    def test_get_settings_returns_agent_name(self):
        """GET /api/settings should return agent_name field"""
        response = self.session.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200, f"GET settings failed: {response.text}"
        data = response.json()
        
        # Verify agent_name field exists
        assert "agent_name" in data, "agent_name field missing from settings"
        # Default should be 'NovaClaw'
        assert data["agent_name"] == "NovaClaw" or data["agent_name"] is not None, "agent_name should have a value"
        print(f"PASS: GET /api/settings returns agent_name: {data['agent_name']}")
    
    def test_get_settings_returns_agent_personality(self):
        """GET /api/settings should return agent_personality field"""
        response = self.session.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200, f"GET settings failed: {response.text}"
        data = response.json()
        
        # Verify agent_personality field exists
        assert "agent_personality" in data, "agent_personality field missing from settings"
        print(f"PASS: GET /api/settings returns agent_personality: '{data['agent_personality']}'")
    
    def test_put_settings_updates_agent_name(self):
        """PUT /api/settings should update agent_name"""
        new_name = "TEST_CustomAgent"
        response = self.session.put(f"{BASE_URL}/api/settings", json={
            "agent_name": new_name
        })
        assert response.status_code == 200, f"PUT settings failed: {response.text}"
        data = response.json()
        
        # Verify agent_name was updated
        assert data["agent_name"] == new_name, f"agent_name not updated: expected {new_name}, got {data['agent_name']}"
        
        # Verify with GET
        get_response = self.session.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["agent_name"] == new_name, "agent_name not persisted"
        print(f"PASS: PUT /api/settings updates agent_name to: {new_name}")
        
        # Reset to default
        self.session.put(f"{BASE_URL}/api/settings", json={"agent_name": "NovaClaw"})
    
    def test_put_settings_updates_agent_personality(self):
        """PUT /api/settings should update agent_personality"""
        new_personality = "TEST_Voce e um assistente especializado em marketing digital."
        response = self.session.put(f"{BASE_URL}/api/settings", json={
            "agent_personality": new_personality
        })
        assert response.status_code == 200, f"PUT settings failed: {response.text}"
        data = response.json()
        
        # Verify agent_personality was updated
        assert data["agent_personality"] == new_personality, f"agent_personality not updated"
        
        # Verify with GET
        get_response = self.session.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["agent_personality"] == new_personality, "agent_personality not persisted"
        print(f"PASS: PUT /api/settings updates agent_personality")
        
        # Reset to default
        self.session.put(f"{BASE_URL}/api/settings", json={"agent_personality": ""})
    
    def test_put_settings_updates_both_agent_fields(self):
        """PUT /api/settings should update both agent_name and agent_personality together"""
        new_name = "TEST_MeuAgente"
        new_personality = "TEST_Voce e um assistente criativo e amigavel."
        
        response = self.session.put(f"{BASE_URL}/api/settings", json={
            "agent_name": new_name,
            "agent_personality": new_personality
        })
        assert response.status_code == 200, f"PUT settings failed: {response.text}"
        data = response.json()
        
        # Verify both fields were updated
        assert data["agent_name"] == new_name, "agent_name not updated"
        assert data["agent_personality"] == new_personality, "agent_personality not updated"
        
        # Verify with GET
        get_response = self.session.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["agent_name"] == new_name, "agent_name not persisted"
        assert get_data["agent_personality"] == new_personality, "agent_personality not persisted"
        print(f"PASS: PUT /api/settings updates both agent_name and agent_personality")
        
        # Reset to defaults
        self.session.put(f"{BASE_URL}/api/settings", json={"agent_name": "NovaClaw", "agent_personality": ""})


class TestHandsFreeConversation:
    """Test conversation creation for hands-free mode with [Voz] prefix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login with admin credentials
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self.created_conv_ids = []
        yield
        
        # Cleanup created conversations
        for conv_id in self.created_conv_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/conversations/{conv_id}")
            except:
                pass
    
    def test_create_conversation_with_voz_prefix(self):
        """POST /api/conversations with [Voz] prefix title (hands-free mode)"""
        title = "[Voz] NovaClaw"
        response = self.session.post(f"{BASE_URL}/api/conversations", json={
            "title": title
        })
        assert response.status_code == 200, f"Create conversation failed: {response.text}"
        data = response.json()
        
        # Verify conversation was created with correct title
        assert data["title"] == title, f"Title mismatch: expected {title}, got {data['title']}"
        assert "id" in data, "Conversation ID missing"
        self.created_conv_ids.append(data["id"])
        
        # Verify with GET
        get_response = self.session.get(f"{BASE_URL}/api/conversations")
        assert get_response.status_code == 200
        convos = get_response.json()
        found = any(c["id"] == data["id"] and c["title"] == title for c in convos)
        assert found, "Conversation with [Voz] prefix not found in list"
        print(f"PASS: Created conversation with [Voz] prefix: {title}")
    
    def test_create_conversation_with_custom_agent_name_voz(self):
        """POST /api/conversations with [Voz] CustomAgentName title"""
        title = "[Voz] MeuAssistente"
        response = self.session.post(f"{BASE_URL}/api/conversations", json={
            "title": title
        })
        assert response.status_code == 200, f"Create conversation failed: {response.text}"
        data = response.json()
        
        assert data["title"] == title, f"Title mismatch"
        self.created_conv_ids.append(data["id"])
        print(f"PASS: Created conversation with custom agent name: {title}")


class TestSettingsAllFields:
    """Test that settings save includes all fields including agent identity"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login with admin credentials
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    def test_settings_save_all_fields(self):
        """PUT /api/settings should save all fields including agent identity"""
        # Get current settings
        get_response = self.session.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        original = get_response.json()
        
        # Update all fields
        update_data = {
            "ollama_url": "http://test-ollama:11434",
            "ollama_model": "test-model:7b",
            "tts_enabled": False,
            "tts_language": "en-US",
            "agent_name": "TEST_AllFieldsAgent",
            "agent_personality": "TEST_All fields personality test"
        }
        
        response = self.session.put(f"{BASE_URL}/api/settings", json=update_data)
        assert response.status_code == 200, f"PUT settings failed: {response.text}"
        data = response.json()
        
        # Verify all fields were updated
        assert data["ollama_url"] == update_data["ollama_url"], "ollama_url not updated"
        assert data["ollama_model"] == update_data["ollama_model"], "ollama_model not updated"
        assert data["tts_enabled"] == update_data["tts_enabled"], "tts_enabled not updated"
        assert data["tts_language"] == update_data["tts_language"], "tts_language not updated"
        assert data["agent_name"] == update_data["agent_name"], "agent_name not updated"
        assert data["agent_personality"] == update_data["agent_personality"], "agent_personality not updated"
        
        print("PASS: All settings fields saved correctly including agent identity")
        
        # Restore original settings
        restore_data = {
            "ollama_url": original.get("ollama_url", "http://localhost:11434"),
            "ollama_model": original.get("ollama_model", "qwen2.5:32b"),
            "tts_enabled": original.get("tts_enabled", True),
            "tts_language": original.get("tts_language", "pt-BR"),
            "agent_name": original.get("agent_name", "NovaClaw"),
            "agent_personality": original.get("agent_personality", "")
        }
        self.session.put(f"{BASE_URL}/api/settings", json=restore_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
