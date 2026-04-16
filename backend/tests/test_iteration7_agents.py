"""
Iteration 7 Tests: Marketing Agency Agents (24 agents + 1 dev)
Tests:
- GET /api/agents returns 25 templates
- POST /api/agents/from-template/{template_id} creates agents from templates
- Verify all squad agent templates exist
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@novaclaw.com"
ADMIN_PASSWORD = "admin123"

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    return response.json().get("access_token")

@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestAgentTemplates:
    """Test agent templates - 25 total (24 marketing + 1 dev)"""
    
    def test_get_agents_returns_25_templates(self, api_client):
        """GET /api/agents should return 25 templates"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        data = response.json()
        assert "templates" in data
        templates = data["templates"]
        
        # Should have 25 templates (24 marketing + 1 dev/coder)
        assert len(templates) == 25, f"Expected 25 templates, got {len(templates)}"
        
        # Verify template structure
        for tmpl in templates:
            assert "id" in tmpl
            assert "name" in tmpl
            assert "description" in tmpl
            assert "icon" in tmpl
            assert "system_prompt" in tmpl
    
    def test_squad1_core_governance_agents_exist(self, api_client):
        """Verify Core & Governance squad agents: orion, sentinel, exec_agent"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        squad1_ids = ["orion", "sentinel", "exec_agent"]
        for agent_id in squad1_ids:
            assert agent_id in template_ids, f"Missing Core & Governance agent: {agent_id}"
    
    def test_squad2_data_diagnostics_agents_exist(self, api_client):
        """Verify Data & Diagnostics squad agents: dash, track, attrib"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        squad2_ids = ["dash", "track", "attrib"]
        for agent_id in squad2_ids:
            assert agent_id in template_ids, f"Missing Data & Diagnostics agent: {agent_id}"
    
    def test_squad3_traffic_agents_exist(self, api_client):
        """Verify Traffic & Performance squad agent: midas"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        assert "midas" in template_ids, "Missing Traffic agent: midas"
    
    def test_squad4_funnel_sales_agents_exist(self, api_client):
        """Verify Funnel & Sales squad agents: hunter, lns, closer"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        squad4_ids = ["hunter", "lns", "closer"]
        for agent_id in squad4_ids:
            assert agent_id in template_ids, f"Missing Funnel & Sales agent: {agent_id}"
    
    def test_squad5_creative_messaging_agents_exist(self, api_client):
        """Verify Creative & Messaging squad agents: nova, mara"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        squad5_ids = ["nova", "mara"]
        for agent_id in squad5_ids:
            assert agent_id in template_ids, f"Missing Creative & Messaging agent: {agent_id}"
    
    def test_squad6_pages_conversion_agents_exist(self, api_client):
        """Verify Pages & Conversion squad agents: lpx, dex, oubas, rex"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        squad6_ids = ["lpx", "dex", "oubas", "rex"]
        for agent_id in squad6_ids:
            assert agent_id in template_ids, f"Missing Pages & Conversion agent: {agent_id}"
    
    def test_squad7_research_product_agents_exist(self, api_client):
        """Verify Research & Product squad agents: atlas, moira"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        squad7_ids = ["atlas", "moira"]
        for agent_id in squad7_ids:
            assert agent_id in template_ids, f"Missing Research & Product agent: {agent_id}"
    
    def test_squad8_reporting_finance_agents_exist(self, api_client):
        """Verify Reporting & Finance squad agents: finn, echo"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        squad8_ids = ["finn", "echo"]
        for agent_id in squad8_ids:
            assert agent_id in template_ids, f"Missing Reporting & Finance agent: {agent_id}"
    
    def test_support_agents_exist(self, api_client):
        """Verify Support agents: nero, eval_agent, archivist, learner"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        support_ids = ["nero", "eval_agent", "archivist", "learner"]
        for agent_id in support_ids:
            assert agent_id in template_ids, f"Missing Support agent: {agent_id}"
    
    def test_general_coder_agent_exists(self, api_client):
        """Verify General purpose agent: coder"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        template_ids = [t["id"] for t in templates]
        
        assert "coder" in template_ids, "Missing General agent: coder"


class TestCreateAgentFromTemplate:
    """Test creating agents from templates"""
    
    def test_create_orion_agent_from_template(self, api_client):
        """POST /api/agents/from-template/orion creates ORION agent"""
        response = api_client.post(f"{BASE_URL}/api/agents/from-template/orion")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["name"] == "ORION - Orquestrador"
        assert "Workflow" in data["icon"]
        assert "orquestrador" in data["system_prompt"].lower()
        
        # Cleanup - delete the created agent
        api_client.delete(f"{BASE_URL}/api/agents/{data['id']}")
    
    def test_create_nova_agent_from_template(self, api_client):
        """POST /api/agents/from-template/nova creates NOVA agent"""
        response = api_client.post(f"{BASE_URL}/api/agents/from-template/nova")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["name"] == "NOVA - Criativos"
        assert "Sparkles" in data["icon"]
        assert "criativos" in data["system_prompt"].lower() or "copy" in data["system_prompt"].lower()
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/agents/{data['id']}")
    
    def test_create_midas_agent_from_template(self, api_client):
        """POST /api/agents/from-template/midas creates MIDAS agent"""
        response = api_client.post(f"{BASE_URL}/api/agents/from-template/midas")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["name"] == "MIDAS - Performance"
        assert "DollarSign" in data["icon"]
        assert "performance" in data["system_prompt"].lower() or "orcamento" in data["system_prompt"].lower()
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/agents/{data['id']}")
    
    def test_create_dash_agent_from_template(self, api_client):
        """POST /api/agents/from-template/dash creates DASH agent"""
        response = api_client.post(f"{BASE_URL}/api/agents/from-template/dash")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["name"] == "DASH - Diagnostico"
        assert "BarChart3" in data["icon"]
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/agents/{data['id']}")
    
    def test_create_invalid_template_returns_404(self, api_client):
        """POST /api/agents/from-template/invalid returns 404"""
        response = api_client.post(f"{BASE_URL}/api/agents/from-template/invalid_template_xyz")
        assert response.status_code == 404


class TestAgentTemplateDetails:
    """Test specific agent template details"""
    
    def test_orion_template_has_correct_details(self, api_client):
        """Verify ORION template has correct name, icon, description"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        orion = next((t for t in templates if t["id"] == "orion"), None)
        
        assert orion is not None
        assert "ORION" in orion["name"]
        assert "Orquestrador" in orion["name"]
        assert orion["icon"] == "Workflow"
        assert "supervisor" in orion["description"].lower() or "coordena" in orion["description"].lower()
    
    def test_sentinel_template_has_shield_icon(self, api_client):
        """Verify SENTINEL template has Shield icon"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        sentinel = next((t for t in templates if t["id"] == "sentinel"), None)
        
        assert sentinel is not None
        assert sentinel["icon"] == "Shield"
        assert "seguranca" in sentinel["description"].lower() or "risco" in sentinel["description"].lower()
    
    def test_closer_template_has_handshake_icon(self, api_client):
        """Verify CLOSER template has Handshake icon"""
        response = api_client.get(f"{BASE_URL}/api/agents")
        assert response.status_code == 200
        
        templates = response.json()["templates"]
        closer = next((t for t in templates if t["id"] == "closer"), None)
        
        assert closer is not None
        assert closer["icon"] == "Handshake"
        assert "fechamento" in closer["description"].lower() or "checkout" in closer["description"].lower()


class TestHealthAndAuth:
    """Basic health and auth tests"""
    
    def test_health_endpoint(self):
        """GET /api/health returns status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
    
    def test_login_with_valid_credentials(self):
        """POST /api/auth/login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
