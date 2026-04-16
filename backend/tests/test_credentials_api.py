"""
NovaClaw Credentials API Tests
Tests for: Credentials CRUD (POST, GET, PUT, DELETE)
New feature added in iteration 2
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@novaclaw.com"
ADMIN_PASSWORD = "admin123"


class TestCredentialsAPI:
    """Credentials management API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_credentials_empty(self):
        """Test GET /api/credentials returns empty list initially"""
        response = requests.get(f"{BASE_URL}/api/credentials", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET credentials: {len(data)} credentials found")
    
    def test_create_credential_telegram(self):
        """Test POST /api/credentials with telegram token"""
        test_token = f"TEST_{uuid.uuid4().hex[:8]}:ABCdefGHIjklMNOpqrSTUvwxYZ123456789"
        response = requests.post(f"{BASE_URL}/api/credentials",
            json={
                "name": "TEST_Telegram Bot",
                "service": "telegram",
                "key_value": test_token
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == "TEST_Telegram Bot"
        assert data["service"] == "telegram"
        assert "key_masked" in data
        assert "key_value" not in data  # Should not return raw value
        assert "created_at" in data
        
        # Verify masking format (first 4 + **** + last 4)
        assert "****" in data["key_masked"]
        assert data["key_masked"].startswith("TEST")
        
        print(f"✓ Created credential: {data['id']} with masked value: {data['key_masked']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/credentials/{data['id']}", headers=self.headers)
        return data
    
    def test_create_credential_github(self):
        """Test POST /api/credentials with GitHub token"""
        test_token = f"ghp_TEST{uuid.uuid4().hex[:20]}abcdefghij"
        response = requests.post(f"{BASE_URL}/api/credentials",
            json={
                "name": "TEST_GitHub Personal Token",
                "service": "github",
                "key_value": test_token
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "github"
        assert "key_masked" in data
        print(f"✓ Created GitHub credential: {data['key_masked']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/credentials/{data['id']}", headers=self.headers)
    
    def test_create_credential_discord(self):
        """Test POST /api/credentials with Discord bot token"""
        test_token = f"TEST_DISCORD_{uuid.uuid4().hex[:30]}"
        response = requests.post(f"{BASE_URL}/api/credentials",
            json={
                "name": "TEST_Discord Bot",
                "service": "discord",
                "key_value": test_token
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "discord"
        print(f"✓ Created Discord credential: {data['key_masked']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/credentials/{data['id']}", headers=self.headers)
    
    def test_get_credentials_shows_masked_values(self):
        """Test GET /api/credentials returns masked values"""
        # Create a credential first
        test_token = "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789"
        create_resp = requests.post(f"{BASE_URL}/api/credentials",
            json={
                "name": "TEST_Masked Value Test",
                "service": "telegram",
                "key_value": test_token
            },
            headers=self.headers
        )
        cred_id = create_resp.json()["id"]
        
        # Get credentials
        response = requests.get(f"{BASE_URL}/api/credentials", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Find our credential
        cred = next((c for c in data if c["id"] == cred_id), None)
        assert cred is not None
        
        # Verify masking
        assert "key_masked" in cred
        assert "key_value" not in cred  # Raw value should not be exposed
        assert cred["key_masked"] == "1234****6789"  # First 4 + **** + last 4
        
        print(f"✓ GET credentials shows masked value: {cred['key_masked']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/credentials/{cred_id}", headers=self.headers)
    
    def test_update_credential(self):
        """Test PUT /api/credentials/{id} updates the key value"""
        # Create first
        create_resp = requests.post(f"{BASE_URL}/api/credentials",
            json={
                "name": "TEST_Update Test",
                "service": "openai",
                "key_value": "sk-test-original-key-12345678"
            },
            headers=self.headers
        )
        cred_id = create_resp.json()["id"]
        
        # Update
        response = requests.put(f"{BASE_URL}/api/credentials/{cred_id}",
            json={"key_value": "sk-test-updated-key-87654321"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Atualizado"
        
        print(f"✓ Updated credential: {cred_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/credentials/{cred_id}", headers=self.headers)
    
    def test_delete_credential(self):
        """Test DELETE /api/credentials/{id}"""
        # Create first
        create_resp = requests.post(f"{BASE_URL}/api/credentials",
            json={
                "name": "TEST_Delete Test",
                "service": "smtp_pass",
                "key_value": "test-smtp-password-12345"
            },
            headers=self.headers
        )
        cred_id = create_resp.json()["id"]
        
        # Delete
        response = requests.delete(f"{BASE_URL}/api/credentials/{cred_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Deletado"
        
        # Verify deletion
        get_resp = requests.get(f"{BASE_URL}/api/credentials", headers=self.headers)
        creds = get_resp.json()
        deleted = next((c for c in creds if c["id"] == cred_id), None)
        assert deleted is None
        
        print(f"✓ Deleted credential: {cred_id}")
    
    def test_delete_nonexistent_credential(self):
        """Test DELETE /api/credentials/{id} with non-existent ID"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(f"{BASE_URL}/api/credentials/{fake_id}",
            headers=self.headers
        )
        # Should return 200 even if not found (idempotent delete)
        assert response.status_code == 200
        print(f"✓ Delete non-existent credential handled gracefully")
    
    def test_credentials_without_auth(self):
        """Test credentials endpoints require authentication"""
        # GET without auth
        response = requests.get(f"{BASE_URL}/api/credentials")
        assert response.status_code == 401
        
        # POST without auth
        response = requests.post(f"{BASE_URL}/api/credentials",
            json={"name": "test", "service": "telegram", "key_value": "test"}
        )
        assert response.status_code == 401
        
        # DELETE without auth
        response = requests.delete(f"{BASE_URL}/api/credentials/fake-id")
        assert response.status_code == 401
        
        print("✓ Credentials endpoints require authentication")
    
    def test_short_key_masking(self):
        """Test masking for short keys (< 8 chars)"""
        response = requests.post(f"{BASE_URL}/api/credentials",
            json={
                "name": "TEST_Short Key",
                "service": "custom",
                "key_value": "short"  # Only 5 chars
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Short keys should just show ****
        assert data["key_masked"] == "****"
        print(f"✓ Short key masked correctly: {data['key_masked']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/credentials/{data['id']}", headers=self.headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
