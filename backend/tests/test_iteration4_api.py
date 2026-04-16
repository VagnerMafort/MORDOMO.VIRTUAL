"""
Iteration 4 API Tests - NovaClaw
Tests for: Agents API, Notes API, Tasks API, Skills execution
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dabcc355-3858-42cc-b0cc-73a58ed79999.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@novaclaw.com"
ADMIN_PASSWORD = "admin123"


class TestAuth:
    """Authentication tests - get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    def test_login_success(self, auth_token):
        """Verify login works and returns token"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Login successful, token obtained")


class TestAgentsAPI:
    """Tests for Agents API - GET, POST, POST from-template, DELETE"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_get_agents_returns_templates(self, headers):
        """GET /api/agents returns custom agents and templates"""
        response = requests.get(f"{BASE_URL}/api/agents", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "custom" in data, "Response should have 'custom' field"
        assert "templates" in data, "Response should have 'templates' field"
        assert isinstance(data["custom"], list)
        assert isinstance(data["templates"], list)
        
        # Verify templates exist (4 templates: coder, researcher, analyst, automator)
        assert len(data["templates"]) == 4, f"Expected 4 templates, got {len(data['templates'])}"
        template_ids = [t["id"] for t in data["templates"]]
        assert "coder" in template_ids
        assert "researcher" in template_ids
        assert "analyst" in template_ids
        assert "automator" in template_ids
        print(f"✓ GET /api/agents returns {len(data['templates'])} templates and {len(data['custom'])} custom agents")
    
    def test_create_custom_agent(self, headers):
        """POST /api/agents creates a custom agent"""
        unique_name = f"TEST_Agent_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique_name,
            "description": "Test agent for iteration 4",
            "icon": "Bot",
            "system_prompt": "You are a test agent.",
            "skills_enabled": ["calculator", "code_executor"]
        }
        response = requests.post(f"{BASE_URL}/api/agents", headers=headers, json=payload)
        assert response.status_code == 200, f"Create agent failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == unique_name
        assert data["description"] == "Test agent for iteration 4"
        assert data["system_prompt"] == "You are a test agent."
        assert data["skills_enabled"] == ["calculator", "code_executor"]
        
        # Verify persistence - GET should include this agent
        get_response = requests.get(f"{BASE_URL}/api/agents", headers=headers)
        agents = get_response.json()["custom"]
        agent_ids = [a["id"] for a in agents]
        assert data["id"] in agent_ids, "Created agent not found in GET response"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/agents/{data['id']}", headers=headers)
        print(f"✓ POST /api/agents created agent '{unique_name}'")
    
    def test_create_agent_from_template_coder(self, headers):
        """POST /api/agents/from-template/coder creates agent from coder template"""
        response = requests.post(f"{BASE_URL}/api/agents/from-template/coder", headers=headers)
        assert response.status_code == 200, f"Create from template failed: {response.text}"
        data = response.json()
        
        # Verify it has coder template properties
        assert "id" in data
        assert data["name"] == "Dev Expert"
        assert "programacao" in data["system_prompt"].lower() or "codigo" in data["system_prompt"].lower()
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/agents/{data['id']}", headers=headers)
        print(f"✓ POST /api/agents/from-template/coder created agent from template")
    
    def test_create_agent_from_template_researcher(self, headers):
        """POST /api/agents/from-template/researcher creates agent from researcher template"""
        response = requests.post(f"{BASE_URL}/api/agents/from-template/researcher", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Pesquisador Web"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/agents/{data['id']}", headers=headers)
        print(f"✓ POST /api/agents/from-template/researcher works")
    
    def test_create_agent_from_invalid_template(self, headers):
        """POST /api/agents/from-template/invalid returns 404"""
        response = requests.post(f"{BASE_URL}/api/agents/from-template/invalid_template", headers=headers)
        assert response.status_code == 404
        print(f"✓ Invalid template returns 404")
    
    def test_delete_agent(self, headers):
        """DELETE /api/agents/{id} deletes an agent"""
        # First create an agent
        payload = {"name": f"TEST_ToDelete_{uuid.uuid4().hex[:8]}", "description": "Will be deleted"}
        create_response = requests.post(f"{BASE_URL}/api/agents", headers=headers, json=payload)
        agent_id = create_response.json()["id"]
        
        # Delete it
        delete_response = requests.delete(f"{BASE_URL}/api/agents/{agent_id}", headers=headers)
        assert delete_response.status_code == 200
        
        # Verify it's gone
        get_response = requests.get(f"{BASE_URL}/api/agents", headers=headers)
        agent_ids = [a["id"] for a in get_response.json()["custom"]]
        assert agent_id not in agent_ids, "Deleted agent still exists"
        print(f"✓ DELETE /api/agents/{agent_id} successfully deleted agent")


class TestNotesAPI:
    """Tests for Notes API - GET, POST, DELETE"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_create_note(self, headers):
        """POST /api/notes creates a note"""
        unique_title = f"TEST_Note_{uuid.uuid4().hex[:8]}"
        payload = {
            "title": unique_title,
            "content": "This is test note content for iteration 4",
            "tags": ["test", "iteration4"]
        }
        response = requests.post(f"{BASE_URL}/api/notes", headers=headers, json=payload)
        assert response.status_code == 200, f"Create note failed: {response.text}"
        data = response.json()
        
        # Verify response
        assert "id" in data
        assert data["title"] == unique_title
        assert data["content"] == "This is test note content for iteration 4"
        assert data["tags"] == ["test", "iteration4"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/notes/{data['id']}", headers=headers)
        print(f"✓ POST /api/notes created note '{unique_title}'")
    
    def test_list_notes(self, headers):
        """GET /api/notes lists notes"""
        # Create a note first
        payload = {"title": f"TEST_ListNote_{uuid.uuid4().hex[:8]}", "content": "Test content"}
        create_response = requests.post(f"{BASE_URL}/api/notes", headers=headers, json=payload)
        note_id = create_response.json()["id"]
        
        # List notes
        response = requests.get(f"{BASE_URL}/api/notes", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify our note is in the list
        note_ids = [n["id"] for n in data]
        assert note_id in note_ids
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/notes/{note_id}", headers=headers)
        print(f"✓ GET /api/notes returns list of notes")
    
    def test_delete_note(self, headers):
        """DELETE /api/notes/{id} deletes a note"""
        # Create a note
        payload = {"title": f"TEST_DeleteNote_{uuid.uuid4().hex[:8]}", "content": "Will be deleted"}
        create_response = requests.post(f"{BASE_URL}/api/notes", headers=headers, json=payload)
        note_id = create_response.json()["id"]
        
        # Delete it
        delete_response = requests.delete(f"{BASE_URL}/api/notes/{note_id}", headers=headers)
        assert delete_response.status_code == 200
        
        # Verify it's gone
        get_response = requests.get(f"{BASE_URL}/api/notes", headers=headers)
        note_ids = [n["id"] for n in get_response.json()]
        assert note_id not in note_ids
        print(f"✓ DELETE /api/notes/{note_id} successfully deleted note")


class TestTasksAPI:
    """Tests for Tasks API - GET, POST, PUT, DELETE"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_create_task(self, headers):
        """POST /api/tasks creates a task"""
        unique_title = f"TEST_Task_{uuid.uuid4().hex[:8]}"
        payload = {
            "title": unique_title,
            "description": "Test task for iteration 4",
            "priority": "high"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", headers=headers, json=payload)
        assert response.status_code == 200, f"Create task failed: {response.text}"
        data = response.json()
        
        # Verify response
        assert "id" in data
        assert data["title"] == unique_title
        assert data["description"] == "Test task for iteration 4"
        assert data["priority"] == "high"
        assert data["done"] == False
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{data['id']}", headers=headers)
        print(f"✓ POST /api/tasks created task '{unique_title}'")
    
    def test_list_tasks(self, headers):
        """GET /api/tasks lists tasks"""
        # Create a task first
        payload = {"title": f"TEST_ListTask_{uuid.uuid4().hex[:8]}", "description": "Test"}
        create_response = requests.post(f"{BASE_URL}/api/tasks", headers=headers, json=payload)
        task_id = create_response.json()["id"]
        
        # List tasks
        response = requests.get(f"{BASE_URL}/api/tasks", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify our task is in the list
        task_ids = [t["id"] for t in data]
        assert task_id in task_ids
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
        print(f"✓ GET /api/tasks returns list of tasks")
    
    def test_update_task_mark_done(self, headers):
        """PUT /api/tasks/{id} marks task as done"""
        # Create a task
        payload = {"title": f"TEST_UpdateTask_{uuid.uuid4().hex[:8]}", "description": "Will be marked done"}
        create_response = requests.post(f"{BASE_URL}/api/tasks", headers=headers, json=payload)
        task_id = create_response.json()["id"]
        
        # Update to mark as done
        update_response = requests.put(f"{BASE_URL}/api/tasks/{task_id}", headers=headers, json={"done": True})
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["done"] == True
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/tasks", headers=headers)
        task = next((t for t in get_response.json() if t["id"] == task_id), None)
        assert task is not None
        assert task["done"] == True
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
        print(f"✓ PUT /api/tasks/{task_id} marked task as done")
    
    def test_delete_task(self, headers):
        """DELETE /api/tasks/{id} deletes a task"""
        # Create a task
        payload = {"title": f"TEST_DeleteTask_{uuid.uuid4().hex[:8]}", "description": "Will be deleted"}
        create_response = requests.post(f"{BASE_URL}/api/tasks", headers=headers, json=payload)
        task_id = create_response.json()["id"]
        
        # Delete it
        delete_response = requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
        assert delete_response.status_code == 200
        
        # Verify it's gone
        get_response = requests.get(f"{BASE_URL}/api/tasks", headers=headers)
        task_ids = [t["id"] for t in get_response.json()]
        assert task_id not in task_ids
        print(f"✓ DELETE /api/tasks/{task_id} successfully deleted task")


class TestSkillsAPI:
    """Tests for Skills - calculator, file_manager, code_executor"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_get_skills_list(self, headers):
        """GET /api/skills returns list of available skills"""
        response = requests.get(f"{BASE_URL}/api/skills", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify expected skills exist
        skill_ids = [s["id"] for s in data]
        expected_skills = ["code_executor", "code_generator", "web_scraper", "url_summarizer", 
                          "file_manager", "notes_tasks", "api_caller", "calculator", 
                          "system_info", "datetime_info"]
        for skill in expected_skills:
            assert skill in skill_ids, f"Skill '{skill}' not found"
        
        print(f"✓ GET /api/skills returns {len(data)} skills")
    
    def test_toggle_skill(self, headers):
        """POST /api/skills/{skill_id}/toggle toggles skill"""
        # Get current state
        get_response = requests.get(f"{BASE_URL}/api/skills", headers=headers)
        skills = get_response.json()
        calculator_skill = next((s for s in skills if s["id"] == "calculator"), None)
        initial_state = calculator_skill["enabled"]
        
        # Toggle
        toggle_response = requests.post(f"{BASE_URL}/api/skills/calculator/toggle", headers=headers)
        assert toggle_response.status_code == 200
        
        # Verify toggle worked
        get_response2 = requests.get(f"{BASE_URL}/api/skills", headers=headers)
        skills2 = get_response2.json()
        calculator_skill2 = next((s for s in skills2 if s["id"] == "calculator"), None)
        assert calculator_skill2["enabled"] != initial_state
        
        # Toggle back to original state
        requests.post(f"{BASE_URL}/api/skills/calculator/toggle", headers=headers)
        print(f"✓ POST /api/skills/calculator/toggle works")


class TestConversationWithAgent:
    """Tests for conversations linked to agents"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_create_conversation_with_agent_id(self, headers):
        """POST /api/conversations with agent_id creates linked conversation"""
        # First create an agent
        agent_payload = {
            "name": f"TEST_ConvAgent_{uuid.uuid4().hex[:8]}",
            "description": "Agent for conversation test",
            "system_prompt": "You are a test agent for conversation linking."
        }
        agent_response = requests.post(f"{BASE_URL}/api/agents", headers=headers, json=agent_payload)
        agent_id = agent_response.json()["id"]
        
        # Create conversation with agent_id
        conv_payload = {
            "title": "Test Conversation with Agent",
            "agent_id": agent_id
        }
        conv_response = requests.post(f"{BASE_URL}/api/conversations", headers=headers, json=conv_payload)
        assert conv_response.status_code == 200, f"Create conversation failed: {conv_response.text}"
        conv_data = conv_response.json()
        
        # Verify agent_id is set
        assert conv_data["agent_id"] == agent_id
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/conversations/{conv_data['id']}", headers=headers)
        requests.delete(f"{BASE_URL}/api/agents/{agent_id}", headers=headers)
        print(f"✓ POST /api/conversations with agent_id creates linked conversation")
    
    def test_conversation_without_agent_id(self, headers):
        """POST /api/conversations without agent_id works"""
        conv_payload = {"title": "Test Conversation without Agent"}
        conv_response = requests.post(f"{BASE_URL}/api/conversations", headers=headers, json=conv_payload)
        assert conv_response.status_code == 200
        conv_data = conv_response.json()
        
        # agent_id should be None
        assert conv_data.get("agent_id") is None
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/conversations/{conv_data['id']}", headers=headers)
        print(f"✓ POST /api/conversations without agent_id works")


class TestSkillExecution:
    """Tests for actual skill execution via message sending"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_health_check(self, headers):
        """Verify API is healthy before skill tests"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        # Verify fallback is available (since Ollama may not be running)
        assert data["fallback"] == True
        print(f"✓ API health check passed, fallback available: {data['fallback']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
