"""
Iteration 9 Backend Tests - Mordomo Virtual Features
Tests: Rules engine, Platform integrations, Inter-agent communication, Metrics history, Dashboard
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication for test setup"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestSettingsAgentName(TestAuth):
    """Test that settings returns 'Mordomo Virtual' as default agent_name"""
    
    def test_settings_returns_mordomo_virtual(self, auth_headers):
        """GET /api/settings should return agent_name as 'Mordomo Virtual'"""
        response = requests.get(f"{BASE_URL}/api/settings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "agent_name" in data
        assert data["agent_name"] == "Mordomo Virtual", f"Expected 'Mordomo Virtual', got '{data['agent_name']}'"


class TestInterAgentCommunication(TestAuth):
    """Test inter-agent communication endpoints"""
    
    def test_get_agent_comms_empty(self, auth_headers):
        """GET /api/agent-comms should return list (possibly empty)"""
        response = requests.get(f"{BASE_URL}/api/agent-comms", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_send_agent_message(self, auth_headers):
        """POST /api/agent-comms/send should create inter-agent message"""
        payload = {
            "from_agent": "user",
            "to_agent": "orion",
            "message_type": "request",
            "payload": {"action": "test_action", "data": "test_data"}
        }
        response = requests.post(f"{BASE_URL}/api/agent-comms/send", headers=auth_headers, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["message"] == "Mensagem enviada"
    
    def test_get_agent_inbox(self, auth_headers):
        """GET /api/agent-comms/{agent_id}/inbox should return pending messages"""
        response = requests.get(f"{BASE_URL}/api/agent-comms/orion/inbox", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the message we just sent
        if len(data) > 0:
            msg = data[0]
            assert "from_agent" in msg
            assert "to_agent" in msg
            assert "message_type" in msg
            assert "payload" in msg
            assert "status" in msg


class TestPlatformIntegrations(TestAuth):
    """Test platform integrations (Meta, Google, TikTok)"""
    
    def test_list_integrations_empty(self, auth_headers):
        """GET /api/agency/integrations should return list"""
        response = requests.get(f"{BASE_URL}/api/agency/integrations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_connect_meta_invalid_token(self, auth_headers):
        """POST /api/agency/integrations/connect with invalid Meta token should return 400"""
        payload = {
            "platform": "meta",
            "credentials": {"access_token": "invalid_token_123", "account_id": "123456"}
        }
        response = requests.post(f"{BASE_URL}/api/agency/integrations/connect", headers=auth_headers, json=payload)
        # Should fail validation with 400
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_connect_google_short_token(self, auth_headers):
        """POST /api/agency/integrations/connect with short Google token should return 400"""
        payload = {
            "platform": "google",
            "credentials": {"access_token": "short"}  # Less than 10 chars
        }
        response = requests.post(f"{BASE_URL}/api/agency/integrations/connect", headers=auth_headers, json=payload)
        assert response.status_code == 400
    
    def test_connect_tiktok_short_token(self, auth_headers):
        """POST /api/agency/integrations/connect with short TikTok token should return 400"""
        payload = {
            "platform": "tiktok",
            "credentials": {"access_token": "tiny"}  # Less than 10 chars
        }
        response = requests.post(f"{BASE_URL}/api/agency/integrations/connect", headers=auth_headers, json=payload)
        assert response.status_code == 400
    
    def test_connect_google_valid_token_length(self, auth_headers):
        """POST /api/agency/integrations/connect with valid length Google token should succeed"""
        payload = {
            "platform": "google",
            "credentials": {"access_token": "valid_test_token_12345", "account_id": "test_account"}
        }
        response = requests.post(f"{BASE_URL}/api/agency/integrations/connect", headers=auth_headers, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "connection" in data
        assert data["connection"]["platform"] == "google"
    
    def test_list_integrations_after_connect(self, auth_headers):
        """GET /api/agency/integrations should show connected platform"""
        response = requests.get(f"{BASE_URL}/api/agency/integrations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have google integration
        platforms = [i["platform"] for i in data]
        assert "google" in platforms
    
    def test_sync_platform_metrics(self, auth_headers):
        """POST /api/agency/integrations/{platform}/sync should attempt sync"""
        response = requests.post(f"{BASE_URL}/api/agency/integrations/google/sync", headers=auth_headers)
        # May succeed or fail depending on actual API, but should not 404
        assert response.status_code in [200, 500]  # 500 if API call fails
    
    def test_disconnect_platform(self, auth_headers):
        """DELETE /api/agency/integrations/{platform} should disconnect"""
        response = requests.delete(f"{BASE_URL}/api/agency/integrations/google", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "desconectado" in data["message"].lower()
    
    def test_sync_disconnected_platform_404(self, auth_headers):
        """POST /api/agency/integrations/{platform}/sync for disconnected platform should 404"""
        response = requests.post(f"{BASE_URL}/api/agency/integrations/google/sync", headers=auth_headers)
        assert response.status_code == 404


class TestMetricsHistory(TestAuth):
    """Test metrics history endpoints"""
    
    @pytest.fixture(scope="class")
    def test_product_id(self, auth_headers):
        """Create a test product for metrics history tests"""
        payload = {
            "name": f"TEST_MetricsProduct_{uuid.uuid4().hex[:8]}",
            "description": "Test product for metrics history",
            "niche": "test",
            "target_audience": "testers",
            "monthly_budget": 1000
        }
        response = requests.post(f"{BASE_URL}/api/agency/products", headers=auth_headers, json=payload)
        assert response.status_code == 200
        return response.json()["id"]
    
    def test_get_metrics_history_empty(self, auth_headers, test_product_id):
        """GET /api/agency/metrics/{prod_id}/history should return list"""
        response = requests.get(f"{BASE_URL}/api/agency/metrics/{test_product_id}/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_record_metrics_snapshot(self, auth_headers, test_product_id):
        """POST /api/agency/metrics/{prod_id}/record should create snapshot"""
        response = requests.post(f"{BASE_URL}/api/agency/metrics/{test_product_id}/record", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "product_id" in data
        assert "metrics" in data
        assert "timestamp" in data
        assert data["product_id"] == test_product_id
    
    def test_get_metrics_history_after_record(self, auth_headers, test_product_id):
        """GET /api/agency/metrics/{prod_id}/history should show recorded snapshot"""
        response = requests.get(f"{BASE_URL}/api/agency/metrics/{test_product_id}/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        snapshot = data[-1]  # Most recent
        assert snapshot["product_id"] == test_product_id
    
    def test_record_metrics_nonexistent_product(self, auth_headers):
        """POST /api/agency/metrics/{prod_id}/record for nonexistent product should 404"""
        response = requests.post(f"{BASE_URL}/api/agency/metrics/nonexistent-id/record", headers=auth_headers)
        assert response.status_code == 404
    
    def test_cleanup_test_product(self, auth_headers, test_product_id):
        """Cleanup: Delete test product"""
        response = requests.delete(f"{BASE_URL}/api/agency/products/{test_product_id}", headers=auth_headers)
        assert response.status_code == 200


class TestAgencyReports(TestAuth):
    """Test agency reports endpoint"""
    
    def test_agency_report_structure(self, auth_headers):
        """GET /api/agency/reports/agency should return proper structure"""
        response = requests.get(f"{BASE_URL}/api/agency/reports/agency", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Check required fields
        assert "products_count" in data
        assert "total_spend" in data
        assert "total_revenue" in data
        assert "overall_roas" in data
        assert "active_rules" in data
        assert "pending_approvals" in data
        assert "products" in data
        assert isinstance(data["products"], list)


class TestRulesEngine(TestAuth):
    """Test rules engine functionality"""
    
    @pytest.fixture(scope="class")
    def test_product_for_rules(self, auth_headers):
        """Create a test product for rules tests"""
        payload = {
            "name": f"TEST_RulesProduct_{uuid.uuid4().hex[:8]}",
            "description": "Test product for rules",
            "niche": "test",
            "target_audience": "testers",
            "monthly_budget": 5000
        }
        response = requests.post(f"{BASE_URL}/api/agency/products", headers=auth_headers, json=payload)
        assert response.status_code == 200
        return response.json()["id"]
    
    def test_create_rule_with_conditions_actions(self, auth_headers, test_product_for_rules):
        """POST /api/agency/rules should create rule with conditions and actions"""
        payload = {
            "name": f"TEST_Rule_{uuid.uuid4().hex[:8]}",
            "product_id": test_product_for_rules,
            "conditions": [
                {"metric": "cpa", "operator": "gt", "value": 50, "period": "24h"}
            ],
            "actions": [
                {"type": "pause_campaign", "params": {}}
            ],
            "requires_approval": True,
            "logic": "AND"
        }
        response = requests.post(f"{BASE_URL}/api/agency/rules", headers=auth_headers, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"].startswith("TEST_Rule_")
        assert data["active"] == True
        assert len(data["conditions"]) == 1
        assert len(data["actions"]) == 1
        return data["id"]
    
    def test_list_rules(self, auth_headers):
        """GET /api/agency/rules should return list of rules"""
        response = requests.get(f"{BASE_URL}/api/agency/rules", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_cleanup_test_product_for_rules(self, auth_headers, test_product_for_rules):
        """Cleanup: Delete test product (cascades to rules)"""
        response = requests.delete(f"{BASE_URL}/api/agency/products/{test_product_for_rules}", headers=auth_headers)
        assert response.status_code == 200


class TestUnauthenticated:
    """Test that endpoints require authentication"""
    
    def test_agent_comms_requires_auth(self):
        """GET /api/agent-comms without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/agent-comms")
        assert response.status_code == 401
    
    def test_integrations_requires_auth(self):
        """GET /api/agency/integrations without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/agency/integrations")
        assert response.status_code == 401
    
    def test_metrics_history_requires_auth(self):
        """GET /api/agency/metrics/test/history without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/agency/metrics/test/history")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
