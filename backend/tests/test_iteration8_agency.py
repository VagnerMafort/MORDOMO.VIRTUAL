"""
Iteration 8 - Agency Module Tests
Tests for Marketing Agency panel with Products, Rules, Approvals, Access Control, Reports
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@novaclaw.com"
ADMIN_PASSWORD = "admin123"

class TestAgencyAccessControl:
    """Test agency access control endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_access_check_admin_has_access(self):
        """GET /api/agency/access/check returns has_access:true for admin"""
        response = requests.get(f"{BASE_URL}/api/agency/access/check", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["has_access"] == True
        assert data["role"] == "admin"
        print(f"PASS: Admin has agency access: {data}")
    
    def test_access_list_admin_only(self):
        """GET /api/agency/access/list returns list for admin"""
        response = requests.get(f"{BASE_URL}/api/agency/access/list", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Access list returned: {len(data)} entries")


class TestAgencyProducts:
    """Test agency products CRUD endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.created_product_ids = []
    
    def teardown_method(self):
        """Cleanup created products"""
        for prod_id in self.created_product_ids:
            try:
                requests.delete(f"{BASE_URL}/api/agency/products/{prod_id}", headers=self.headers)
            except:
                pass
    
    def test_create_product_with_metrics(self):
        """POST /api/agency/products creates a product with metrics"""
        product_data = {
            "name": f"TEST_Product_{uuid.uuid4().hex[:8]}",
            "description": "Test product description",
            "niche": "E-commerce",
            "target_audience": "Adults 25-45",
            "monthly_budget": 5000.0
        }
        response = requests.post(f"{BASE_URL}/api/agency/products", json=product_data, headers=self.headers)
        assert response.status_code == 200, f"Create product failed: {response.text}"
        data = response.json()
        
        # Verify product fields
        assert data["name"] == product_data["name"]
        assert data["niche"] == product_data["niche"]
        assert data["target_audience"] == product_data["target_audience"]
        assert data["monthly_budget"] == product_data["monthly_budget"]
        assert data["status"] == "active"
        assert "id" in data
        
        # Verify metrics structure
        assert "metrics" in data
        metrics = data["metrics"]
        assert metrics["ctr"] == 0
        assert metrics["cpc"] == 0
        assert metrics["cpa"] == 0
        assert metrics["roas"] == 0
        assert metrics["conversions"] == 0
        assert metrics["spend"] == 0
        assert metrics["revenue"] == 0
        
        self.created_product_ids.append(data["id"])
        print(f"PASS: Product created with metrics: {data['id']}")
        return data
    
    def test_list_products(self):
        """GET /api/agency/products lists products"""
        # First create a product
        product_data = {
            "name": f"TEST_ListProduct_{uuid.uuid4().hex[:8]}",
            "niche": "SaaS"
        }
        create_resp = requests.post(f"{BASE_URL}/api/agency/products", json=product_data, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_product_ids.append(created["id"])
        
        # List products
        response = requests.get(f"{BASE_URL}/api/agency/products", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify our product is in the list
        product_ids = [p["id"] for p in data]
        assert created["id"] in product_ids
        print(f"PASS: Products listed: {len(data)} products")
    
    def test_delete_product(self):
        """DELETE /api/agency/products/{id} deletes product"""
        # Create a product
        product_data = {"name": f"TEST_DeleteProduct_{uuid.uuid4().hex[:8]}"}
        create_resp = requests.post(f"{BASE_URL}/api/agency/products", json=product_data, headers=self.headers)
        assert create_resp.status_code == 200
        prod_id = create_resp.json()["id"]
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/api/agency/products/{prod_id}", headers=self.headers)
        assert response.status_code == 200
        assert "deletado" in response.json()["message"].lower()
        
        # Verify it's gone
        list_resp = requests.get(f"{BASE_URL}/api/agency/products", headers=self.headers)
        product_ids = [p["id"] for p in list_resp.json()]
        assert prod_id not in product_ids
        print(f"PASS: Product deleted: {prod_id}")


class TestAgencyCampaigns:
    """Test agency campaigns endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and create a test product"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a product for campaigns
        product_data = {"name": f"TEST_CampaignProduct_{uuid.uuid4().hex[:8]}"}
        prod_resp = requests.post(f"{BASE_URL}/api/agency/products", json=product_data, headers=self.headers)
        assert prod_resp.status_code == 200
        self.product_id = prod_resp.json()["id"]
        self.created_campaign_ids = []
    
    def teardown_method(self):
        """Cleanup"""
        for camp_id in self.created_campaign_ids:
            try:
                requests.delete(f"{BASE_URL}/api/agency/campaigns/{camp_id}", headers=self.headers)
            except:
                pass
        try:
            requests.delete(f"{BASE_URL}/api/agency/products/{self.product_id}", headers=self.headers)
        except:
            pass
    
    def test_create_campaign_linked_to_product(self):
        """POST /api/agency/campaigns creates campaign linked to product"""
        campaign_data = {
            "product_id": self.product_id,
            "name": f"TEST_Campaign_{uuid.uuid4().hex[:8]}",
            "platform": "meta",
            "objective": "conversions",
            "daily_budget": 100.0
        }
        response = requests.post(f"{BASE_URL}/api/agency/campaigns", json=campaign_data, headers=self.headers)
        assert response.status_code == 200, f"Create campaign failed: {response.text}"
        data = response.json()
        
        assert data["product_id"] == self.product_id
        assert data["name"] == campaign_data["name"]
        assert data["platform"] == "meta"
        assert data["daily_budget"] == 100.0
        assert "metrics" in data
        
        self.created_campaign_ids.append(data["id"])
        print(f"PASS: Campaign created linked to product: {data['id']}")


class TestAgencyRules:
    """Test agency rules engine endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and create a test product"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a product for rules
        product_data = {"name": f"TEST_RuleProduct_{uuid.uuid4().hex[:8]}"}
        prod_resp = requests.post(f"{BASE_URL}/api/agency/products", json=product_data, headers=self.headers)
        assert prod_resp.status_code == 200
        self.product_id = prod_resp.json()["id"]
        self.created_rule_ids = []
    
    def teardown_method(self):
        """Cleanup"""
        for rule_id in self.created_rule_ids:
            try:
                requests.delete(f"{BASE_URL}/api/agency/rules/{rule_id}", headers=self.headers)
            except:
                pass
        try:
            requests.delete(f"{BASE_URL}/api/agency/products/{self.product_id}", headers=self.headers)
        except:
            pass
    
    def test_create_rule_with_conditions_and_actions(self):
        """POST /api/agency/rules creates a rule with conditions and actions"""
        rule_data = {
            "name": f"TEST_Rule_{uuid.uuid4().hex[:8]}",
            "product_id": self.product_id,
            "conditions": [
                {"metric": "cpa", "operator": "gt", "value": 50.0, "period": "24h"}
            ],
            "actions": [
                {"type": "pause_campaign", "params": {}}
            ],
            "requires_approval": True,
            "logic": "AND"
        }
        response = requests.post(f"{BASE_URL}/api/agency/rules", json=rule_data, headers=self.headers)
        assert response.status_code == 200, f"Create rule failed: {response.text}"
        data = response.json()
        
        assert data["name"] == rule_data["name"]
        assert data["product_id"] == self.product_id
        assert len(data["conditions"]) == 1
        assert data["conditions"][0]["metric"] == "cpa"
        assert data["conditions"][0]["operator"] == "gt"
        assert data["conditions"][0]["value"] == 50.0
        assert len(data["actions"]) == 1
        assert data["actions"][0]["type"] == "pause_campaign"
        assert data["requires_approval"] == True
        assert data["active"] == True
        
        self.created_rule_ids.append(data["id"])
        print(f"PASS: Rule created with conditions/actions: {data['id']}")
        return data
    
    def test_list_rules(self):
        """GET /api/agency/rules lists rules"""
        # Create a rule first
        rule_data = {
            "name": f"TEST_ListRule_{uuid.uuid4().hex[:8]}",
            "product_id": self.product_id,
            "conditions": [{"metric": "ctr", "operator": "lt", "value": 1.0, "period": "24h"}],
            "actions": [{"type": "alert", "params": {}}]
        }
        create_resp = requests.post(f"{BASE_URL}/api/agency/rules", json=rule_data, headers=self.headers)
        assert create_resp.status_code == 200
        created = create_resp.json()
        self.created_rule_ids.append(created["id"])
        
        # List rules
        response = requests.get(f"{BASE_URL}/api/agency/rules", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        rule_ids = [r["id"] for r in data]
        assert created["id"] in rule_ids
        print(f"PASS: Rules listed: {len(data)} rules")
    
    def test_toggle_rule_active_state(self):
        """PUT /api/agency/rules/{id}/toggle toggles rule active state"""
        # Create a rule
        rule_data = {
            "name": f"TEST_ToggleRule_{uuid.uuid4().hex[:8]}",
            "product_id": self.product_id,
            "conditions": [{"metric": "spend", "operator": "gt", "value": 1000, "period": "24h"}],
            "actions": [{"type": "alert", "params": {}}]
        }
        create_resp = requests.post(f"{BASE_URL}/api/agency/rules", json=rule_data, headers=self.headers)
        assert create_resp.status_code == 200
        rule_id = create_resp.json()["id"]
        initial_active = create_resp.json()["active"]
        self.created_rule_ids.append(rule_id)
        
        # Toggle it
        response = requests.put(f"{BASE_URL}/api/agency/rules/{rule_id}/toggle", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["active"] == (not initial_active)
        
        # Toggle again
        response2 = requests.put(f"{BASE_URL}/api/agency/rules/{rule_id}/toggle", headers=self.headers)
        assert response2.status_code == 200
        assert response2.json()["active"] == initial_active
        print(f"PASS: Rule toggle works: {rule_id}")


class TestAgencyApprovals:
    """Test agency approval queue endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_approval_queue(self):
        """GET /api/agency/approvals returns approval queue"""
        response = requests.get(f"{BASE_URL}/api/agency/approvals", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Approval queue returned: {len(data)} items")


class TestAgencyReports:
    """Test agency reports endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_agency_report_overview(self):
        """GET /api/agency/reports/agency returns agency overview"""
        response = requests.get(f"{BASE_URL}/api/agency/reports/agency", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify report structure
        assert "products_count" in data
        assert "total_spend" in data
        assert "total_revenue" in data
        assert "total_conversions" in data
        assert "overall_roas" in data
        assert "active_rules" in data
        assert "pending_approvals" in data
        assert "products" in data
        assert isinstance(data["products"], list)
        
        print(f"PASS: Agency report returned: {data['products_count']} products, ROAS: {data['overall_roas']}")


class TestAgencyAccessGrant:
    """Test granting agency access to users"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_grant_access_to_user(self):
        """POST /api/agency/access/grant grants access to a user email"""
        # First register a test user
        test_email = f"test_agency_{uuid.uuid4().hex[:8]}@test.com"
        register_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test Agency User"
        })
        
        if register_resp.status_code == 200:
            # Grant access
            response = requests.post(f"{BASE_URL}/api/agency/access/grant", json={
                "user_email": test_email,
                "granted": True
            }, headers=self.headers)
            assert response.status_code == 200
            data = response.json()
            assert "concedido" in data["message"].lower()
            print(f"PASS: Access granted to {test_email}")
        else:
            # User might already exist, try granting anyway
            print(f"Note: Could not register test user, skipping grant test")
            pytest.skip("Could not create test user for grant test")


class TestAgencyUnauthorized:
    """Test that non-admin users without access get 403"""
    
    def test_access_denied_without_token(self):
        """Agency endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/agency/products")
        assert response.status_code == 401
        print("PASS: Unauthenticated request returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
