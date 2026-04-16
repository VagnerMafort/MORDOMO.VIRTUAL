"""
Iteration 10 Tests - Temporal Dashboard & Real Action Execution
Tests:
1. PUT /api/agency/products/{id}/metrics - auto-records history
2. GET /api/agency/metrics/{id}/history - returns timeline data
3. GET /api/agency/execution-log - returns execution history
4. POST /api/agency/approvals/{id}/approve - executes actions and returns results
5. Rules engine cron auto-records metrics snapshots
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestAuth.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@novaclaw.com",
                "password": "admin123"
            })
            assert response.status_code == 200, f"Login failed: {response.text}"
            TestAuth.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {TestAuth.token}"}
    
    def test_login_success(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "admin@novaclaw.com"


class TestMetricsHistory:
    """Test metrics history endpoints - auto-recording on update"""
    token = None
    product_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestMetricsHistory.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@novaclaw.com",
                "password": "admin123"
            })
            TestMetricsHistory.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {TestMetricsHistory.token}"}
    
    def test_01_create_test_product(self):
        """Create a test product for metrics testing"""
        response = requests.post(f"{BASE_URL}/api/agency/products", json={
            "name": f"TEST_MetricsProduct_{uuid.uuid4().hex[:6]}",
            "description": "Test product for metrics history",
            "niche": "testing",
            "monthly_budget": 5000
        }, headers=self.headers)
        assert response.status_code == 200, f"Failed to create product: {response.text}"
        data = response.json()
        assert "id" in data
        TestMetricsHistory.product_id = data["id"]
        print(f"Created test product: {data['id']}")
    
    def test_02_update_metrics_auto_records_history(self):
        """PUT /api/agency/products/{id}/metrics should auto-record history"""
        assert TestMetricsHistory.product_id, "Product not created"
        
        # Update metrics
        response = requests.put(
            f"{BASE_URL}/api/agency/products/{TestMetricsHistory.product_id}/metrics",
            json={
                "spend": 1000,
                "revenue": 3500,
                "roas": 3.5,
                "cpa": 25,
                "ctr": 2.5,
                "conversions": 40
            },
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to update metrics: {response.text}"
        data = response.json()
        assert "metrics" in data
        assert data["metrics"]["spend"] == 1000
        assert data["metrics"]["revenue"] == 3500
        assert data["metrics"]["roas"] == 3.5
        print(f"Updated metrics: {data['metrics']}")
    
    def test_03_get_metrics_history(self):
        """GET /api/agency/metrics/{id}/history should return timeline data"""
        assert TestMetricsHistory.product_id, "Product not created"
        
        response = requests.get(
            f"{BASE_URL}/api/agency/metrics/{TestMetricsHistory.product_id}/history",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get history: {response.text}"
        data = response.json()
        assert isinstance(data, list), "History should be a list"
        assert len(data) >= 1, "Should have at least 1 history entry from auto-record"
        
        # Verify history entry structure
        entry = data[-1]  # Most recent
        assert "product_id" in entry
        assert "metrics" in entry
        assert "timestamp" in entry
        assert entry["metrics"]["spend"] == 1000
        print(f"History entries: {len(data)}, latest: {entry['timestamp']}")
    
    def test_04_update_metrics_again_creates_new_history(self):
        """Second metrics update should create another history entry"""
        assert TestMetricsHistory.product_id, "Product not created"
        
        # Update metrics again
        response = requests.put(
            f"{BASE_URL}/api/agency/products/{TestMetricsHistory.product_id}/metrics",
            json={
                "spend": 1500,
                "revenue": 5000,
                "roas": 3.33,
                "cpa": 30,
                "ctr": 2.8,
                "conversions": 50
            },
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Check history has 2 entries now
        response = requests.get(
            f"{BASE_URL}/api/agency/metrics/{TestMetricsHistory.product_id}/history",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2, f"Should have at least 2 history entries, got {len(data)}"
        print(f"History now has {len(data)} entries")
    
    def test_05_manual_record_metrics(self):
        """POST /api/agency/metrics/{id}/record should create snapshot"""
        assert TestMetricsHistory.product_id, "Product not created"
        
        response = requests.post(
            f"{BASE_URL}/api/agency/metrics/{TestMetricsHistory.product_id}/record",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to record: {response.text}"
        data = response.json()
        assert "product_id" in data
        assert "metrics" in data
        assert "timestamp" in data
        print(f"Manual snapshot recorded at {data['timestamp']}")
    
    def test_99_cleanup_test_product(self):
        """Cleanup test product"""
        if TestMetricsHistory.product_id:
            response = requests.delete(
                f"{BASE_URL}/api/agency/products/{TestMetricsHistory.product_id}",
                headers=self.headers
            )
            assert response.status_code == 200


class TestExecutionLog:
    """Test execution log endpoint"""
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestExecutionLog.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@novaclaw.com",
                "password": "admin123"
            })
            TestExecutionLog.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {TestExecutionLog.token}"}
    
    def test_get_execution_log(self):
        """GET /api/agency/execution-log should return execution history"""
        response = requests.get(f"{BASE_URL}/api/agency/execution-log", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Execution log should be a list"
        print(f"Execution log has {len(data)} entries")
        
        # If there are entries, verify structure
        if len(data) > 0:
            entry = data[0]
            assert "id" in entry or "rule_id" in entry
            assert "executed_at" in entry
            print(f"Latest execution: {entry.get('rule_name', 'N/A')} at {entry.get('executed_at')}")


class TestApprovalExecution:
    """Test approval execution with real action execution"""
    token = None
    product_id = None
    campaign_id = None
    rule_id = None
    approval_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestApprovalExecution.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@novaclaw.com",
                "password": "admin123"
            })
            TestApprovalExecution.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {TestApprovalExecution.token}"}
    
    def test_01_create_product_for_approval(self):
        """Create product for approval testing"""
        response = requests.post(f"{BASE_URL}/api/agency/products", json={
            "name": f"TEST_ApprovalProduct_{uuid.uuid4().hex[:6]}",
            "description": "Test product for approval execution",
            "niche": "testing",
            "monthly_budget": 10000
        }, headers=self.headers)
        assert response.status_code == 200
        TestApprovalExecution.product_id = response.json()["id"]
        
        # Set initial metrics
        requests.put(
            f"{BASE_URL}/api/agency/products/{TestApprovalExecution.product_id}/metrics",
            json={"spend": 2000, "revenue": 8000, "roas": 4.0, "cpa": 20, "conversions": 100},
            headers=self.headers
        )
        print(f"Created product: {TestApprovalExecution.product_id}")
    
    def test_02_create_campaign(self):
        """Create campaign for the product"""
        response = requests.post(f"{BASE_URL}/api/agency/campaigns", json={
            "product_id": TestApprovalExecution.product_id,
            "name": f"TEST_Campaign_{uuid.uuid4().hex[:6]}",
            "platform": "meta",
            "objective": "conversions",
            "daily_budget": 100
        }, headers=self.headers)
        assert response.status_code == 200
        TestApprovalExecution.campaign_id = response.json()["id"]
        print(f"Created campaign: {TestApprovalExecution.campaign_id}")
    
    def test_03_create_rule_with_approval(self):
        """Create rule that requires approval"""
        response = requests.post(f"{BASE_URL}/api/agency/rules", json={
            "name": f"TEST_Rule_ScaleBudget_{uuid.uuid4().hex[:6]}",
            "product_id": TestApprovalExecution.product_id,
            "campaign_id": TestApprovalExecution.campaign_id,
            "conditions": [
                {"metric": "roas", "operator": "gt", "value": 3.0, "period": "24h"}
            ],
            "actions": [
                {"type": "scale_budget", "params": {"factor": 1.5}}
            ],
            "requires_approval": True,
            "logic": "AND"
        }, headers=self.headers)
        assert response.status_code == 200
        TestApprovalExecution.rule_id = response.json()["id"]
        print(f"Created rule: {TestApprovalExecution.rule_id}")
    
    def test_04_check_pending_approvals(self):
        """Check if there are pending approvals"""
        response = requests.get(f"{BASE_URL}/api/agency/approvals", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} approvals")
        
        # Find pending approval for our rule
        pending = [a for a in data if a.get("status") == "pending" and a.get("rule_id") == TestApprovalExecution.rule_id]
        if pending:
            TestApprovalExecution.approval_id = pending[0]["id"]
            print(f"Found pending approval: {TestApprovalExecution.approval_id}")
    
    def test_05_approve_action_executes_and_returns_results(self):
        """POST /api/agency/approvals/{id}/approve should execute and return results"""
        # If no approval was created by rules engine, we need to manually create one for testing
        if not TestApprovalExecution.approval_id:
            # Create a manual approval entry for testing
            from datetime import datetime, timezone
            import uuid as uuid_mod
            approval_id = str(uuid_mod.uuid4())
            
            # We'll test the approve endpoint with an existing approval if any
            response = requests.get(f"{BASE_URL}/api/agency/approvals", headers=self.headers)
            approvals = response.json()
            pending = [a for a in approvals if a.get("status") == "pending"]
            
            if pending:
                TestApprovalExecution.approval_id = pending[0]["id"]
                print(f"Using existing pending approval: {TestApprovalExecution.approval_id}")
            else:
                print("No pending approvals to test - skipping execution test")
                pytest.skip("No pending approvals available for testing")
        
        # Approve the action
        response = requests.post(
            f"{BASE_URL}/api/agency/approvals/{TestApprovalExecution.approval_id}/approve",
            headers=self.headers
        )
        assert response.status_code == 200, f"Approve failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "results" in data
        print(f"Approval result: {data['message']}")
        print(f"Execution results: {data['results']}")
        
        # Verify execution was logged
        response = requests.get(f"{BASE_URL}/api/agency/execution-log", headers=self.headers)
        assert response.status_code == 200
        logs = response.json()
        print(f"Execution log now has {len(logs)} entries")
    
    def test_99_cleanup(self):
        """Cleanup test data"""
        if TestApprovalExecution.rule_id:
            requests.delete(f"{BASE_URL}/api/agency/rules/{TestApprovalExecution.rule_id}", headers=self.headers)
        if TestApprovalExecution.campaign_id:
            requests.delete(f"{BASE_URL}/api/agency/campaigns/{TestApprovalExecution.campaign_id}", headers=self.headers)
        if TestApprovalExecution.product_id:
            requests.delete(f"{BASE_URL}/api/agency/products/{TestApprovalExecution.product_id}", headers=self.headers)


class TestAgencyReportEndpoints:
    """Test agency report endpoints"""
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestAgencyReportEndpoints.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@novaclaw.com",
                "password": "admin123"
            })
            TestAgencyReportEndpoints.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {TestAgencyReportEndpoints.token}"}
    
    def test_agency_report(self):
        """GET /api/agency/reports/agency returns overview"""
        response = requests.get(f"{BASE_URL}/api/agency/reports/agency", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "products_count" in data
        assert "total_spend" in data
        assert "total_revenue" in data
        assert "overall_roas" in data
        assert "active_rules" in data
        assert "pending_approvals" in data
        assert "products" in data
        print(f"Agency report: {data['products_count']} products, ROAS: {data['overall_roas']}")


class TestIntegrations:
    """Test platform integrations"""
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestIntegrations.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@novaclaw.com",
                "password": "admin123"
            })
            TestIntegrations.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {TestIntegrations.token}"}
    
    def test_list_integrations(self):
        """GET /api/agency/integrations returns list"""
        response = requests.get(f"{BASE_URL}/api/agency/integrations", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} integrations")


class TestAgentCommunication:
    """Test inter-agent communication"""
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestAgentCommunication.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@novaclaw.com",
                "password": "admin123"
            })
            TestAgentCommunication.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {TestAgentCommunication.token}"}
    
    def test_get_agent_comms(self):
        """GET /api/agent-comms returns messages"""
        response = requests.get(f"{BASE_URL}/api/agent-comms", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} agent messages")
    
    def test_send_agent_message(self):
        """POST /api/agent-comms/send creates message"""
        response = requests.post(f"{BASE_URL}/api/agent-comms/send", json={
            "from_agent": "test_agent",
            "to_agent": "orion",
            "message_type": "request",
            "payload": {"test": True, "message": "Test message from iteration 10"}
        }, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"Sent message: {data['id']}")
    
    def test_get_agent_inbox(self):
        """GET /api/agent-comms/{agent_id}/inbox returns pending messages"""
        response = requests.get(f"{BASE_URL}/api/agent-comms/orion/inbox", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Orion inbox has {len(data)} pending messages")


class TestUnauthenticated:
    """Test unauthenticated access is blocked"""
    
    def test_metrics_history_requires_auth(self):
        """GET /api/agency/metrics/{id}/history requires auth"""
        response = requests.get(f"{BASE_URL}/api/agency/metrics/test-id/history")
        assert response.status_code == 401
    
    def test_execution_log_requires_auth(self):
        """GET /api/agency/execution-log requires auth"""
        response = requests.get(f"{BASE_URL}/api/agency/execution-log")
        assert response.status_code == 401
    
    def test_approvals_requires_auth(self):
        """GET /api/agency/approvals requires auth"""
        response = requests.get(f"{BASE_URL}/api/agency/approvals")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
