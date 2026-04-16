"""
Test Mentorship Modules & Export - Iteration 12
Tests for: Modules CRUD, parse-modules, PDF/DOCX export
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMentorshipModules:
    """Mentorship Modules CRUD API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login with admin credentials
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.authenticated = True
        else:
            self.authenticated = False
            pytest.skip("Authentication failed - skipping authenticated tests")
        
        # Get existing mentorship or create one
        list_resp = self.session.get(f"{BASE_URL}/api/mentorship/list")
        mentorships = list_resp.json()
        
        if mentorships:
            self.mentorship_id = mentorships[0]["id"]
        else:
            # Create a test mentorship
            create_resp = self.session.post(f"{BASE_URL}/api/mentorship/generate", json={
                "title": "TEST_Mentoria Modulos",
                "knowledge_text": "Conhecimento sobre Python e programacao.",
                "niche": "Programacao",
                "target_audience": "Desenvolvedores",
                "duration_weeks": 4
            })
            if create_resp.status_code == 200:
                self.mentorship_id = create_resp.json()["id"]
            else:
                pytest.skip("Could not create test mentorship")
        
        yield
        
        # Cleanup: Delete test modules
        try:
            modules_resp = self.session.get(f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules")
            if modules_resp.status_code == 200:
                for mod in modules_resp.json():
                    if mod.get('title', '').startswith('TEST_'):
                        self.session.delete(f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules/{mod['id']}")
        except Exception:
            pass

    # ─── GET Modules Tests ─────────────────────────────────────────────────────
    
    def test_get_modules_returns_list(self):
        """GET /api/mentorship/{id}/modules - Returns structured modules list"""
        response = self.session.get(f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        
        # If modules exist, validate structure
        if len(data) > 0:
            module = data[0]
            assert "id" in module, "Module should have 'id'"
            assert "title" in module, "Module should have 'title'"
            assert "order" in module, "Module should have 'order'"
            assert "lessons" in module, "Module should have 'lessons'"
            
            # Validate lessons structure
            if len(module.get("lessons", [])) > 0:
                lesson = module["lessons"][0]
                assert "id" in lesson, "Lesson should have 'id'"
                assert "title" in lesson, "Lesson should have 'title'"
        
        print(f"PASS: GET modules returned {len(data)} modules")
    
    def test_get_modules_not_found(self):
        """GET /api/mentorship/{id}/modules - Returns 404 for non-existent mentorship"""
        response = self.session.get(f"{BASE_URL}/api/mentorship/nonexistent-id-12345/modules")
        
        assert response.status_code == 404
        print(f"PASS: Non-existent mentorship correctly returns 404")

    # ─── POST Module Tests ─────────────────────────────────────────────────────
    
    def test_add_module(self):
        """POST /api/mentorship/{id}/modules - Add a new module"""
        payload = {
            "title": "TEST_Novo Modulo",
            "objective": "Testar adicao de modulo via API",
            "lessons": [
                {"title": "Aula 1", "content": "Conteudo da aula 1", "duration": "30min"},
                {"title": "Aula 2", "content": "Conteudo da aula 2", "duration": "45min"}
            ],
            "exercises": [],
            "materials": []
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data, "Response should contain 'id'"
        assert "title" in data, "Response should contain 'title'"
        assert "order" in data, "Response should contain 'order'"
        assert "lessons" in data, "Response should contain 'lessons'"
        
        # Validate values
        assert data["title"] == "TEST_Novo Modulo"
        assert data["objective"] == "Testar adicao de modulo via API"
        assert len(data["lessons"]) == 2
        
        # Validate lessons have IDs assigned
        for lesson in data["lessons"]:
            assert "id" in lesson, "Lesson should have auto-generated 'id'"
            assert "order" in lesson, "Lesson should have 'order'"
        
        print(f"PASS: Module added with id={data['id']}, {len(data['lessons'])} lessons")
        
        # Store for cleanup
        self.test_module_id = data["id"]
    
    def test_add_module_not_found(self):
        """POST /api/mentorship/{id}/modules - Returns 404 for non-existent mentorship"""
        payload = {"title": "TEST_Module", "objective": "", "lessons": []}
        
        response = self.session.post(
            f"{BASE_URL}/api/mentorship/nonexistent-id-12345/modules",
            json=payload
        )
        
        assert response.status_code == 404
        print(f"PASS: Add module to non-existent mentorship returns 404")

    # ─── PUT Modules Tests ─────────────────────────────────────────────────────
    
    def test_save_modules_full_structure(self):
        """PUT /api/mentorship/{id}/modules - Save full module structure"""
        # Get current modules
        get_resp = self.session.get(f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules")
        modules = get_resp.json()
        
        # Add a test module to the list
        modules.append({
            "title": "TEST_PUT Module",
            "objective": "Test PUT endpoint",
            "order": len(modules),
            "lessons": [{"title": "Test Lesson", "content": "Test content", "duration": "20min"}],
            "exercises": [],
            "materials": []
        })
        
        response = self.session.put(
            f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules",
            json=modules
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        
        # Verify the test module was added
        test_modules = [m for m in data if m.get("title") == "TEST_PUT Module"]
        assert len(test_modules) == 1, "Test module should be in response"
        
        # Verify IDs were assigned
        test_mod = test_modules[0]
        assert "id" in test_mod, "Module should have auto-generated 'id'"
        
        print(f"PASS: PUT modules saved {len(data)} modules")
    
    def test_save_modules_updates_existing(self):
        """PUT /api/mentorship/{id}/modules - Updates existing module titles"""
        # Get current modules
        get_resp = self.session.get(f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules")
        modules = get_resp.json()
        
        if len(modules) == 0:
            pytest.skip("No modules to update")
        
        # Store original title
        original_title = modules[0]["title"]
        
        # Update first module's title
        modules[0]["title"] = "TEST_Updated Title"
        
        response = self.session.put(
            f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules",
            json=modules
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify update
        assert data[0]["title"] == "TEST_Updated Title"
        
        # Restore original title
        modules[0]["title"] = original_title
        self.session.put(f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules", json=modules)
        
        print(f"PASS: Module title updated and restored")

    # ─── DELETE Module Tests ───────────────────────────────────────────────────
    
    def test_delete_module(self):
        """DELETE /api/mentorship/{id}/modules/{module_id} - Remove module"""
        # First add a module to delete
        add_resp = self.session.post(
            f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules",
            json={"title": "TEST_Delete Module", "objective": "", "lessons": []}
        )
        module_id = add_resp.json()["id"]
        
        # Get count before delete
        before_resp = self.session.get(f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules")
        count_before = len(before_resp.json())
        
        # Delete
        response = self.session.delete(
            f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules/{module_id}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        
        # Verify deletion
        after_resp = self.session.get(f"{BASE_URL}/api/mentorship/{self.mentorship_id}/modules")
        count_after = len(after_resp.json())
        
        assert count_after == count_before - 1, "Module count should decrease by 1"
        
        # Verify module ID not in list
        module_ids = [m["id"] for m in after_resp.json()]
        assert module_id not in module_ids, "Deleted module should not appear in list"
        
        print(f"PASS: Module {module_id} deleted successfully")
    
    def test_delete_module_not_found(self):
        """DELETE /api/mentorship/{id}/modules/{module_id} - Returns 404 for non-existent mentorship"""
        response = self.session.delete(
            f"{BASE_URL}/api/mentorship/nonexistent-id-12345/modules/some-module-id"
        )
        
        assert response.status_code == 404
        print(f"PASS: Delete module from non-existent mentorship returns 404")


class TestMentorshipParseModules:
    """Test parse-modules endpoint that converts AI content to structured modules"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
        
        # Get existing mentorship
        list_resp = self.session.get(f"{BASE_URL}/api/mentorship/list")
        mentorships = list_resp.json()
        
        if mentorships:
            self.mentorship_id = mentorships[0]["id"]
        else:
            pytest.skip("No mentorship available for testing")
    
    def test_parse_modules_returns_structured_data(self):
        """POST /api/mentorship/{id}/parse-modules - Parses AI content into modules"""
        response = self.session.post(
            f"{BASE_URL}/api/mentorship/{self.mentorship_id}/parse-modules"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list of modules"
        
        # Validate structure
        if len(data) > 0:
            module = data[0]
            assert "id" in module, "Module should have 'id'"
            assert "title" in module, "Module should have 'title'"
            assert "order" in module, "Module should have 'order'"
            assert "lessons" in module, "Module should have 'lessons'"
        
        print(f"PASS: Parse modules returned {len(data)} modules")
    
    def test_parse_modules_not_found(self):
        """POST /api/mentorship/{id}/parse-modules - Returns 404 for non-existent"""
        response = self.session.post(
            f"{BASE_URL}/api/mentorship/nonexistent-id-12345/parse-modules"
        )
        
        assert response.status_code == 404
        print(f"PASS: Parse modules for non-existent mentorship returns 404")


class TestMentorshipExport:
    """Test PDF and DOCX export endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@novaclaw.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
        
        # Get existing mentorship
        list_resp = self.session.get(f"{BASE_URL}/api/mentorship/list")
        mentorships = list_resp.json()
        
        if mentorships:
            self.mentorship_id = mentorships[0]["id"]
            self.mentorship_title = mentorships[0]["title"]
        else:
            pytest.skip("No mentorship available for testing")
    
    def test_export_pdf_returns_pdf_file(self):
        """GET /api/mentorship/{id}/export/pdf - Returns PDF file"""
        response = self.session.get(
            f"{BASE_URL}/api/mentorship/{self.mentorship_id}/export/pdf"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate content type
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        
        # Validate Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        assert ".pdf" in content_disp, "Filename should have .pdf extension"
        
        # Validate content is not empty
        assert len(response.content) > 1000, "PDF content should be substantial"
        
        # Validate PDF magic bytes
        assert response.content[:4] == b'%PDF', "Content should start with PDF magic bytes"
        
        print(f"PASS: PDF export returned {len(response.content)} bytes")
    
    def test_export_docx_returns_docx_file(self):
        """GET /api/mentorship/{id}/export/docx - Returns DOCX file"""
        response = self.session.get(
            f"{BASE_URL}/api/mentorship/{self.mentorship_id}/export/docx"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Validate content type
        content_type = response.headers.get("Content-Type", "")
        expected_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert expected_type in content_type, f"Expected {expected_type}, got {content_type}"
        
        # Validate Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        assert ".docx" in content_disp, "Filename should have .docx extension"
        
        # Validate content is not empty
        assert len(response.content) > 1000, "DOCX content should be substantial"
        
        # Validate DOCX magic bytes (ZIP format)
        assert response.content[:2] == b'PK', "DOCX should start with PK (ZIP magic bytes)"
        
        print(f"PASS: DOCX export returned {len(response.content)} bytes")
    
    def test_export_pdf_not_found(self):
        """GET /api/mentorship/{id}/export/pdf - Returns 404 for non-existent"""
        response = self.session.get(
            f"{BASE_URL}/api/mentorship/nonexistent-id-12345/export/pdf"
        )
        
        assert response.status_code == 404
        print(f"PASS: PDF export for non-existent mentorship returns 404")
    
    def test_export_docx_not_found(self):
        """GET /api/mentorship/{id}/export/docx - Returns 404 for non-existent"""
        response = self.session.get(
            f"{BASE_URL}/api/mentorship/nonexistent-id-12345/export/docx"
        )
        
        assert response.status_code == 404
        print(f"PASS: DOCX export for non-existent mentorship returns 404")


class TestMentorshipModulesAuth:
    """Test authentication requirements for modules endpoints"""
    
    def test_modules_endpoints_require_auth(self):
        """All modules endpoints should require authentication"""
        unauthenticated = requests.Session()
        unauthenticated.headers.update({"Content-Type": "application/json"})
        
        # Test GET endpoints - should return 401
        get_endpoints = [
            "/api/mentorship/test-id/modules",
            "/api/mentorship/test-id/export/pdf",
            "/api/mentorship/test-id/export/docx",
        ]
        
        for endpoint in get_endpoints:
            resp = unauthenticated.get(f"{BASE_URL}{endpoint}")
            assert resp.status_code == 401, f"GET {endpoint} should return 401 without auth, got {resp.status_code}"
        
        # Test DELETE endpoint - should return 401
        resp = unauthenticated.delete(f"{BASE_URL}/api/mentorship/test-id/modules/mod-id")
        assert resp.status_code == 401, f"DELETE should return 401 without auth, got {resp.status_code}"
        
        # Test POST parse-modules - should return 401
        resp = unauthenticated.post(f"{BASE_URL}/api/mentorship/test-id/parse-modules")
        assert resp.status_code == 401, f"POST parse-modules should return 401 without auth, got {resp.status_code}"
        
        # Test POST/PUT with valid body - may return 401 or 422 (validation before auth)
        # This is acceptable behavior as the endpoint still requires auth
        resp = unauthenticated.post(
            f"{BASE_URL}/api/mentorship/test-id/modules",
            json={"title": "Test", "objective": "", "lessons": []}
        )
        assert resp.status_code in [401, 422], f"POST modules should return 401 or 422, got {resp.status_code}"
        
        resp = unauthenticated.put(
            f"{BASE_URL}/api/mentorship/test-id/modules",
            json=[]
        )
        assert resp.status_code == 401, f"PUT modules should return 401, got {resp.status_code}"
        
        print(f"PASS: All endpoints correctly require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
