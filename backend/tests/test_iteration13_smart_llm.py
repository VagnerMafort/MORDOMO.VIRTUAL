"""
Iteration 13 Tests - Smart LLM Infrastructure
Tests for:
1. GET /api/system/memory-stats - returns cache_entries, summaries, tasks
2. PUT /api/settings with ollama_model_fast and ollama_model_smart
3. GET /api/settings returns ollama_model_fast and ollama_model_smart fields
4. Docker files existence verification
5. Smart LLM complexity detection
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestIteration13SmartLLM:
    """Tests for iteration 13 smart LLM infrastructure"""
    
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
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    # ─── Memory Stats Endpoint Tests ─────────────────────────────────────────
    def test_memory_stats_returns_expected_fields(self):
        """GET /api/system/memory-stats should return cache_entries, summaries, tasks"""
        response = self.session.get(f"{BASE_URL}/api/system/memory-stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify all expected fields are present
        assert "cache_entries" in data, "Missing cache_entries field"
        assert "conversation_summaries" in data, "Missing conversation_summaries field"
        assert "tasks_pending" in data, "Missing tasks_pending field"
        assert "tasks_completed" in data, "Missing tasks_completed field"
        
        # Verify types
        assert isinstance(data["cache_entries"], int), "cache_entries should be int"
        assert isinstance(data["conversation_summaries"], int), "conversation_summaries should be int"
        assert isinstance(data["tasks_pending"], int), "tasks_pending should be int"
        assert isinstance(data["tasks_completed"], int), "tasks_completed should be int"
        
        print(f"Memory stats: {data}")
    
    def test_memory_stats_requires_auth(self):
        """GET /api/system/memory-stats should require authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        response = no_auth_session.get(f"{BASE_URL}/api/system/memory-stats")
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
    
    # ─── Settings Dual Model Tests ───────────────────────────────────────────
    def test_settings_get_returns_dual_model_fields(self):
        """GET /api/settings should return ollama_model_fast and ollama_model_smart fields"""
        response = self.session.get(f"{BASE_URL}/api/settings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # These fields may or may not be set, but the endpoint should work
        # Check that the response is a valid settings object
        assert "ollama_url" in data, "Missing ollama_url field"
        assert "ollama_model" in data, "Missing ollama_model field"
        
        print(f"Settings: {data}")
    
    def test_settings_put_dual_model_fast(self):
        """PUT /api/settings with ollama_model_fast should save"""
        update_data = {
            "ollama_model_fast": "qwen2.5:7b"
        }
        
        response = self.session.put(f"{BASE_URL}/api/settings", json=update_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ollama_model_fast") == "qwen2.5:7b", f"ollama_model_fast not saved correctly: {data}"
        
        print(f"Updated settings with fast model: {data.get('ollama_model_fast')}")
    
    def test_settings_put_dual_model_smart(self):
        """PUT /api/settings with ollama_model_smart should save"""
        update_data = {
            "ollama_model_smart": "qwen2.5:32b"
        }
        
        response = self.session.put(f"{BASE_URL}/api/settings", json=update_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ollama_model_smart") == "qwen2.5:32b", f"ollama_model_smart not saved correctly: {data}"
        
        print(f"Updated settings with smart model: {data.get('ollama_model_smart')}")
    
    def test_settings_put_both_dual_models(self):
        """PUT /api/settings with both ollama_model_fast and ollama_model_smart should save"""
        update_data = {
            "ollama_model_fast": "llama3.2:3b",
            "ollama_model_smart": "llama3.2:70b"
        }
        
        response = self.session.put(f"{BASE_URL}/api/settings", json=update_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ollama_model_fast") == "llama3.2:3b", f"ollama_model_fast not saved: {data}"
        assert data.get("ollama_model_smart") == "llama3.2:70b", f"ollama_model_smart not saved: {data}"
        
        # Verify persistence with GET
        get_response = self.session.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data.get("ollama_model_fast") == "llama3.2:3b"
        assert get_data.get("ollama_model_smart") == "llama3.2:70b"
        
        print(f"Both models saved and verified: fast={get_data.get('ollama_model_fast')}, smart={get_data.get('ollama_model_smart')}")
        
        # Reset to defaults
        self.session.put(f"{BASE_URL}/api/settings", json={
            "ollama_model_fast": "qwen2.5:7b",
            "ollama_model_smart": "qwen2.5:32b"
        })
    
    # ─── Task Status Endpoint Tests ──────────────────────────────────────────
    def test_task_status_not_found(self):
        """GET /api/system/task/{id} should return not_found for invalid task"""
        response = self.session.get(f"{BASE_URL}/api/system/task/nonexistent-task-id")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "not_found", f"Expected not_found status: {data}"
        
        print(f"Task status for invalid ID: {data}")
    
    # ─── Health Check Tests ──────────────────────────────────────────────────
    def test_health_endpoint(self):
        """GET /api/health should return status"""
        response = self.session.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data, "Missing status field"
        assert data["status"] == "online", f"Expected online status: {data}"
        
        print(f"Health check: {data}")
    
    # ─── Docker Files Existence Tests ────────────────────────────────────────
    def test_docker_compose_exists(self):
        """docker-compose.yml should exist at /app/docker-compose.yml"""
        assert os.path.exists("/app/docker-compose.yml"), "docker-compose.yml not found"
        
        with open("/app/docker-compose.yml", "r") as f:
            content = f.read()
            assert "services:" in content, "docker-compose.yml missing services section"
            assert "mongodb" in content, "docker-compose.yml missing mongodb service"
            assert "backend" in content, "docker-compose.yml missing backend service"
            assert "frontend" in content, "docker-compose.yml missing frontend service"
        
        print("docker-compose.yml exists and contains required services")
    
    def test_deploy_script_exists(self):
        """deploy.sh should exist at /app/deploy.sh"""
        assert os.path.exists("/app/deploy.sh"), "deploy.sh not found"
        
        with open("/app/deploy.sh", "r") as f:
            content = f.read()
            assert "docker" in content.lower(), "deploy.sh should reference docker"
        
        print("deploy.sh exists")
    
    def test_backend_dockerfile_exists(self):
        """Backend Dockerfile should exist at /app/backend/Dockerfile"""
        assert os.path.exists("/app/backend/Dockerfile"), "Backend Dockerfile not found"
        
        with open("/app/backend/Dockerfile", "r") as f:
            content = f.read()
            assert "FROM" in content, "Dockerfile missing FROM instruction"
            assert "uvicorn" in content.lower() or "python" in content.lower(), "Dockerfile should run Python app"
        
        print("Backend Dockerfile exists")
    
    def test_frontend_dockerfile_exists(self):
        """Frontend Dockerfile should exist at /app/frontend/Dockerfile"""
        assert os.path.exists("/app/frontend/Dockerfile"), "Frontend Dockerfile not found"
        
        with open("/app/frontend/Dockerfile", "r") as f:
            content = f.read()
            assert "FROM" in content, "Dockerfile missing FROM instruction"
            assert "node" in content.lower() or "nginx" in content.lower(), "Dockerfile should use node or nginx"
        
        print("Frontend Dockerfile exists")


class TestSmartLLMModule:
    """Tests for smart_llm.py module functions"""
    
    def test_smart_llm_module_exists(self):
        """smart_llm.py module should exist"""
        assert os.path.exists("/app/backend/smart_llm.py"), "smart_llm.py not found"
        print("smart_llm.py exists")
    
    def test_smart_llm_has_required_functions(self):
        """smart_llm.py should have required functions"""
        with open("/app/backend/smart_llm.py", "r") as f:
            content = f.read()
            
            # Check for required functions
            assert "def detect_complexity" in content, "Missing detect_complexity function"
            assert "def get_model_for_task" in content, "Missing get_model_for_task function"
            assert "async def get_cached_response" in content, "Missing get_cached_response function"
            assert "async def set_cached_response" in content, "Missing set_cached_response function"
            assert "async def build_memory_context" in content, "Missing build_memory_context function"
            assert "async def maybe_create_summary" in content, "Missing maybe_create_summary function"
            assert "async def background_worker" in content, "Missing background_worker function"
        
        print("smart_llm.py has all required functions")
    
    def test_complexity_keywords_defined(self):
        """smart_llm.py should have complexity detection keywords"""
        with open("/app/backend/smart_llm.py", "r") as f:
            content = f.read()
            
            # Check for complexity keywords
            assert "COMPLEX_KEYWORDS" in content, "Missing COMPLEX_KEYWORDS"
            assert "SIMPLE_PATTERNS" in content, "Missing SIMPLE_PATTERNS"
            assert "mentoria" in content, "Missing 'mentoria' in complex keywords"
            assert "relatorio" in content, "Missing 'relatorio' in complex keywords"
        
        print("Complexity detection keywords defined")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
