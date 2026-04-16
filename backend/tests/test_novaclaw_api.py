"""
NovaClaw API Backend Tests
Tests for: Auth, Conversations, Messages, Skills, Settings
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@novaclaw.com"
ADMIN_PASSWORD = "admin123"
TEST_EMAIL = f"test_{uuid.uuid4().hex[:8]}@test.com"
TEST_PASSWORD = "password123"
TEST_NAME = "TestUser"


class TestHealthAndRoot:
    """Health check and root endpoint tests"""
    
    def test_root_endpoint(self):
        """Test API root returns version info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "NovaClaw" in data["message"]
        print(f"✓ Root endpoint: {data}")
    
    def test_health_endpoint(self):
        """Test health check returns status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "ollama" in data
        assert "fallback" in data
        print(f"✓ Health check: {data}")


class TestAuthentication:
    """Authentication flow tests"""
    
    def test_login_admin_success(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['email']}")
        return data
    
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print(f"✓ Invalid login rejected: {data['detail']}")
    
    def test_register_new_user(self):
        """Test user registration"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL.lower()
        assert data["user"]["name"] == TEST_NAME
        assert data["user"]["role"] == "user"
        print(f"✓ User registered: {data['user']['email']}")
        return data
    
    def test_register_duplicate_email(self):
        """Test registration with existing email fails"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": ADMIN_EMAIL,
            "password": "somepassword",
            "name": "Duplicate"
        })
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"✓ Duplicate registration rejected: {data['detail']}")
    
    def test_auth_me_with_token(self):
        """Test /auth/me returns user info with valid token"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["access_token"]
        
        # Then check /me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        assert "password_hash" not in data  # Should not expose password
        print(f"✓ Auth me: {data['email']}")
    
    def test_auth_me_without_token(self):
        """Test /auth/me fails without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ Auth me without token rejected")
    
    def test_logout(self):
        """Test logout endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Logout: {data['message']}")
    
    def test_refresh_token(self):
        """Test token refresh"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        refresh_token = login_resp.json()["refresh_token"]
        
        # Refresh
        response = requests.post(f"{BASE_URL}/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print("✓ Token refresh successful")


class TestConversations:
    """Conversation CRUD tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_create_conversation(self):
        """Test creating a new conversation"""
        response = requests.post(f"{BASE_URL}/api/conversations", 
            json={"title": "TEST_Conversa de Teste"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "TEST_Conversa de Teste"
        assert "created_at" in data
        assert "updated_at" in data
        print(f"✓ Conversation created: {data['id']}")
        return data
    
    def test_list_conversations(self):
        """Test listing conversations"""
        response = requests.get(f"{BASE_URL}/api/conversations", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} conversations")
    
    def test_update_conversation(self):
        """Test renaming a conversation"""
        # Create first
        create_resp = requests.post(f"{BASE_URL}/api/conversations",
            json={"title": "TEST_Original Title"},
            headers=self.headers
        )
        conv_id = create_resp.json()["id"]
        
        # Update
        response = requests.put(f"{BASE_URL}/api/conversations/{conv_id}",
            json={"title": "TEST_Updated Title"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Verify by listing
        list_resp = requests.get(f"{BASE_URL}/api/conversations", headers=self.headers)
        convs = list_resp.json()
        updated = next((c for c in convs if c["id"] == conv_id), None)
        assert updated is not None
        assert updated["title"] == "TEST_Updated Title"
        print(f"✓ Conversation renamed: {conv_id}")
    
    def test_delete_conversation(self):
        """Test deleting a conversation"""
        # Create first
        create_resp = requests.post(f"{BASE_URL}/api/conversations",
            json={"title": "TEST_To Delete"},
            headers=self.headers
        )
        conv_id = create_resp.json()["id"]
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/conversations/{conv_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Verify deleted
        list_resp = requests.get(f"{BASE_URL}/api/conversations", headers=self.headers)
        convs = list_resp.json()
        deleted = next((c for c in convs if c["id"] == conv_id), None)
        assert deleted is None
        print(f"✓ Conversation deleted: {conv_id}")
    
    def test_conversation_without_auth(self):
        """Test conversation endpoints require auth"""
        response = requests.get(f"{BASE_URL}/api/conversations")
        assert response.status_code == 401
        print("✓ Conversations require auth")


class TestMessages:
    """Message tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and create conversation"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a conversation for testing
        conv_resp = requests.post(f"{BASE_URL}/api/conversations",
            json={"title": "TEST_Message Test Conv"},
            headers=self.headers
        )
        self.conv_id = conv_resp.json()["id"]
    
    def test_list_messages_empty(self):
        """Test listing messages in empty conversation"""
        response = requests.get(f"{BASE_URL}/api/conversations/{self.conv_id}/messages",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
        print(f"✓ Empty messages list for conv {self.conv_id}")
    
    def test_send_message_returns_stream(self):
        """Test sending a message returns SSE stream"""
        response = requests.post(
            f"{BASE_URL}/api/conversations/{self.conv_id}/messages",
            json={"content": "Ola, teste rapido"},
            headers=self.headers,
            stream=True
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        # Read some of the stream
        content = ""
        for line in response.iter_lines(decode_unicode=True):
            if line:
                content += line + "\n"
                if "done" in line:
                    break
        
        assert "data:" in content
        print(f"✓ Message sent with SSE stream")
    
    def test_messages_without_auth(self):
        """Test message endpoints require auth"""
        response = requests.get(f"{BASE_URL}/api/conversations/{self.conv_id}/messages")
        assert response.status_code == 401
        print("✓ Messages require auth")


class TestSkills:
    """Skills system tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_skills(self):
        """Test listing available skills"""
        response = requests.get(f"{BASE_URL}/api/skills", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check skill structure
        skill = data[0]
        assert "id" in skill
        assert "name" in skill
        assert "description" in skill
        assert "enabled" in skill
        print(f"✓ Listed {len(data)} skills")
    
    def test_toggle_skill(self):
        """Test toggling a skill on/off"""
        # Get current state
        list_resp = requests.get(f"{BASE_URL}/api/skills", headers=self.headers)
        skills = list_resp.json()
        skill = skills[0]
        original_enabled = skill["enabled"]
        
        # Toggle
        response = requests.post(f"{BASE_URL}/api/skills/{skill['id']}/toggle",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        
        # Verify toggle
        new_enabled = skill["id"] in data["enabled"]
        assert new_enabled != original_enabled
        print(f"✓ Skill {skill['id']} toggled: {original_enabled} -> {new_enabled}")
        
        # Toggle back
        requests.post(f"{BASE_URL}/api/skills/{skill['id']}/toggle", headers=self.headers)
    
    def test_skills_without_auth(self):
        """Test skills endpoints require auth"""
        response = requests.get(f"{BASE_URL}/api/skills")
        assert response.status_code == 401
        print("✓ Skills require auth")


class TestSettings:
    """Settings tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_settings(self):
        """Test getting user settings"""
        response = requests.get(f"{BASE_URL}/api/settings", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "ollama_url" in data
        assert "ollama_model" in data
        assert "tts_enabled" in data
        assert "tts_language" in data
        assert "skills_enabled" in data
        print(f"✓ Settings retrieved: ollama_url={data['ollama_url']}")
    
    def test_update_settings(self):
        """Test updating settings"""
        # Get current
        get_resp = requests.get(f"{BASE_URL}/api/settings", headers=self.headers)
        original = get_resp.json()
        
        # Update
        response = requests.put(f"{BASE_URL}/api/settings",
            json={
                "ollama_url": "http://test:11434",
                "ollama_model": "test-model",
                "tts_enabled": not original.get("tts_enabled", True)
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ollama_url"] == "http://test:11434"
        assert data["ollama_model"] == "test-model"
        print("✓ Settings updated")
        
        # Restore original
        requests.put(f"{BASE_URL}/api/settings",
            json={
                "ollama_url": original.get("ollama_url"),
                "ollama_model": original.get("ollama_model"),
                "tts_enabled": original.get("tts_enabled")
            },
            headers=self.headers
        )
    
    def test_settings_without_auth(self):
        """Test settings endpoints require auth"""
        response = requests.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 401
        print("✓ Settings require auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
