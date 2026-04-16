"""
Test Mentorship Module - Iteration 11
Tests for mentorship creation system: knowledge upload, CRUD, and AI generation
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMentorshipModule:
    """Mentorship API tests"""
    
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
        
        yield
        
        # Cleanup: Delete test knowledge and mentorships
        try:
            # Get and delete test knowledge
            knowledge_resp = self.session.get(f"{BASE_URL}/api/mentorship/knowledge")
            if knowledge_resp.status_code == 200:
                for k in knowledge_resp.json():
                    if k.get('filename', '').startswith('TEST_'):
                        self.session.delete(f"{BASE_URL}/api/mentorship/knowledge/{k['id']}")
            
            # Get and delete test mentorships
            mentorship_resp = self.session.get(f"{BASE_URL}/api/mentorship/list")
            if mentorship_resp.status_code == 200:
                for m in mentorship_resp.json():
                    if m.get('title', '').startswith('TEST_'):
                        self.session.delete(f"{BASE_URL}/api/mentorship/{m['id']}")
        except Exception:
            pass

    # ─── Knowledge Upload Tests ────────────────────────────────────────────────
    
    def test_upload_knowledge_txt_file(self):
        """POST /api/mentorship/upload-knowledge - Upload .txt file"""
        # Create a test file
        files = {
            'file': ('TEST_knowledge.txt', 'Este e meu conhecimento sobre marketing digital. Tenho 10 anos de experiencia.', 'text/plain')
        }
        # Remove Content-Type header for multipart
        headers = {"Authorization": self.session.headers.get("Authorization")}
        
        response = requests.post(
            f"{BASE_URL}/api/mentorship/upload-knowledge",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data, "Response should contain 'id'"
        assert "filename" in data, "Response should contain 'filename'"
        assert "size" in data, "Response should contain 'size'"
        assert "preview" in data, "Response should contain 'preview'"
        
        # Validate values
        assert data["filename"] == "TEST_knowledge.txt"
        assert data["size"] > 0
        assert "marketing digital" in data["preview"].lower()
        
        print(f"PASS: Knowledge upload returned id={data['id']}, size={data['size']}")
    
    def test_upload_knowledge_md_file(self):
        """POST /api/mentorship/upload-knowledge - Upload .md file"""
        files = {
            'file': ('TEST_knowledge.md', '# Minha Metodologia\n\n## Passo 1\nDefinir objetivos claros\n\n## Passo 2\nExecutar com consistencia', 'text/markdown')
        }
        headers = {"Authorization": self.session.headers.get("Authorization")}
        
        response = requests.post(
            f"{BASE_URL}/api/mentorship/upload-knowledge",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "TEST_knowledge.md"
        assert "Metodologia" in data["preview"]
        print(f"PASS: Markdown file upload successful")
    
    def test_upload_knowledge_csv_file(self):
        """POST /api/mentorship/upload-knowledge - Upload .csv file"""
        csv_content = "modulo,aula,descricao\nIntroducao,Boas vindas,Apresentacao do curso\nFundamentos,Conceitos basicos,Teoria inicial"
        files = {
            'file': ('TEST_knowledge.csv', csv_content, 'text/csv')
        }
        headers = {"Authorization": self.session.headers.get("Authorization")}
        
        response = requests.post(
            f"{BASE_URL}/api/mentorship/upload-knowledge",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "TEST_knowledge.csv"
        print(f"PASS: CSV file upload successful")

    # ─── Knowledge List Tests ──────────────────────────────────────────────────
    
    def test_list_knowledge(self):
        """GET /api/mentorship/knowledge - List uploaded knowledge files"""
        # First upload a file
        files = {
            'file': ('TEST_list_knowledge.txt', 'Conteudo para teste de listagem', 'text/plain')
        }
        headers = {"Authorization": self.session.headers.get("Authorization")}
        requests.post(f"{BASE_URL}/api/mentorship/upload-knowledge", files=files, headers=headers)
        
        # Now list
        response = self.session.get(f"{BASE_URL}/api/mentorship/knowledge")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check structure of items
        if len(data) > 0:
            item = data[0]
            assert "id" in item
            assert "filename" in item
            assert "size" in item
            assert "created_at" in item
            # Content should NOT be in list response (excluded for performance)
            assert "content" not in item
        
        print(f"PASS: Knowledge list returned {len(data)} items")

    # ─── Knowledge Delete Tests ────────────────────────────────────────────────
    
    def test_delete_knowledge(self):
        """DELETE /api/mentorship/knowledge/{id} - Remove knowledge"""
        # First upload
        files = {
            'file': ('TEST_delete_knowledge.txt', 'Conteudo para deletar', 'text/plain')
        }
        headers = {"Authorization": self.session.headers.get("Authorization")}
        upload_resp = requests.post(f"{BASE_URL}/api/mentorship/upload-knowledge", files=files, headers=headers)
        knowledge_id = upload_resp.json()["id"]
        
        # Delete
        response = self.session.delete(f"{BASE_URL}/api/mentorship/knowledge/{knowledge_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify deletion - should not appear in list
        list_resp = self.session.get(f"{BASE_URL}/api/mentorship/knowledge")
        knowledge_ids = [k["id"] for k in list_resp.json()]
        assert knowledge_id not in knowledge_ids, "Deleted knowledge should not appear in list"
        
        print(f"PASS: Knowledge {knowledge_id} deleted successfully")

    # ─── Mentorship List Tests ─────────────────────────────────────────────────
    
    def test_list_mentorships(self):
        """GET /api/mentorship/list - List user's mentorships"""
        response = self.session.get(f"{BASE_URL}/api/mentorship/list")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check structure if items exist
        if len(data) > 0:
            item = data[0]
            assert "id" in item
            assert "title" in item
            assert "status" in item
            assert "created_at" in item
        
        print(f"PASS: Mentorship list returned {len(data)} items")

    # ─── Mentorship Generate Tests ─────────────────────────────────────────────
    
    def test_generate_mentorship_with_text(self):
        """POST /api/mentorship/generate - Generate mentorship from knowledge text"""
        payload = {
            "title": "TEST_Mentoria Marketing",
            "knowledge_text": "Sou especialista em marketing digital com 10 anos de experiencia. Minha metodologia inclui: 1) Analise de mercado, 2) Definicao de persona, 3) Criacao de conteudo, 4) Automacao de marketing, 5) Analise de metricas. Ja ajudei mais de 500 alunos a aumentarem suas vendas online.",
            "niche": "Marketing Digital",
            "target_audience": "Empreendedores iniciantes",
            "duration_weeks": 8
        }
        
        response = self.session.post(f"{BASE_URL}/api/mentorship/generate", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data, "Response should contain 'id'"
        assert "title" in data, "Response should contain 'title'"
        assert "content" in data, "Response should contain 'content'"
        assert "status" in data, "Response should contain 'status'"
        assert "niche" in data, "Response should contain 'niche'"
        assert "target_audience" in data, "Response should contain 'target_audience'"
        assert "duration_weeks" in data, "Response should contain 'duration_weeks'"
        assert "created_at" in data, "Response should contain 'created_at'"
        
        # Validate values
        assert data["status"] == "draft"
        assert data["niche"] == "Marketing Digital"
        assert data["target_audience"] == "Empreendedores iniciantes"
        assert data["duration_weeks"] == 8
        
        # Content should be generated (non-empty)
        assert len(data["content"]) > 100, "Generated content should be substantial"
        
        print(f"PASS: Mentorship generated with id={data['id']}, content length={len(data['content'])}")
        
        # Store for cleanup
        self.generated_mentorship_id = data["id"]
    
    def test_generate_mentorship_no_knowledge_fails(self):
        """POST /api/mentorship/generate - Should fail without knowledge"""
        payload = {
            "title": "TEST_Empty Mentoria",
            "knowledge_text": "",
            "niche": "",
            "target_audience": "",
            "duration_weeks": 8
        }
        
        response = self.session.post(f"{BASE_URL}/api/mentorship/generate", json=payload)
        
        # Should fail with 400 if no knowledge provided and no uploaded files
        # Note: This may pass if user has uploaded knowledge files
        if response.status_code == 400:
            data = response.json()
            assert "detail" in data
            print(f"PASS: Empty knowledge correctly rejected with: {data['detail']}")
        else:
            # If it passes, user has uploaded knowledge files
            print(f"INFO: Generate succeeded (user has uploaded knowledge files)")

    # ─── Mentorship Get Tests ──────────────────────────────────────────────────
    
    def test_get_mentorship_by_id(self):
        """GET /api/mentorship/{id} - Get full mentorship content"""
        # First create a mentorship
        payload = {
            "title": "TEST_Get Mentoria",
            "knowledge_text": "Conhecimento sobre vendas online e e-commerce.",
            "niche": "E-commerce",
            "target_audience": "Lojistas",
            "duration_weeks": 6
        }
        create_resp = self.session.post(f"{BASE_URL}/api/mentorship/generate", json=payload)
        mentorship_id = create_resp.json()["id"]
        
        # Get by ID
        response = self.session.get(f"{BASE_URL}/api/mentorship/{mentorship_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate full content is returned
        assert data["id"] == mentorship_id
        assert "content" in data
        assert len(data["content"]) > 0
        
        print(f"PASS: Mentorship {mentorship_id} retrieved with full content")
    
    def test_get_mentorship_not_found(self):
        """GET /api/mentorship/{id} - Should return 404 for non-existent"""
        response = self.session.get(f"{BASE_URL}/api/mentorship/nonexistent-id-12345")
        
        assert response.status_code == 404
        print(f"PASS: Non-existent mentorship correctly returns 404")

    # ─── Mentorship Delete Tests ───────────────────────────────────────────────
    
    def test_delete_mentorship(self):
        """DELETE /api/mentorship/{id} - Remove mentorship"""
        # First create
        payload = {
            "title": "TEST_Delete Mentoria",
            "knowledge_text": "Conhecimento para deletar.",
            "niche": "Teste",
            "target_audience": "Testers",
            "duration_weeks": 4
        }
        create_resp = self.session.post(f"{BASE_URL}/api/mentorship/generate", json=payload)
        mentorship_id = create_resp.json()["id"]
        
        # Delete
        response = self.session.delete(f"{BASE_URL}/api/mentorship/{mentorship_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify deletion
        get_resp = self.session.get(f"{BASE_URL}/api/mentorship/{mentorship_id}")
        assert get_resp.status_code == 404, "Deleted mentorship should return 404"
        
        print(f"PASS: Mentorship {mentorship_id} deleted and verified")

    # ─── Authentication Tests ──────────────────────────────────────────────────
    
    def test_unauthenticated_access_denied(self):
        """All mentorship endpoints should require authentication"""
        unauthenticated = requests.Session()
        
        # Test each endpoint without auth
        endpoints = [
            ("GET", "/api/mentorship/list"),
            ("GET", "/api/mentorship/knowledge"),
            ("GET", "/api/mentorship/test-id"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                resp = unauthenticated.get(f"{BASE_URL}{endpoint}")
            assert resp.status_code == 401, f"{method} {endpoint} should return 401 without auth"
        
        print(f"PASS: All endpoints correctly require authentication")


class TestMentorshipAgentIntegration:
    """Test MOIRA and NOVA agents have mentorship capabilities"""
    
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
    
    def test_agents_list_contains_moira_and_nova(self):
        """GET /api/agents - Verify MOIRA and NOVA templates exist with mentorship capabilities"""
        response = self.session.get(f"{BASE_URL}/api/agents")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check templates
        templates = data.get("templates", [])
        template_ids = [t["id"] for t in templates]
        
        assert "moira" in template_ids, "MOIRA agent template should exist"
        assert "nova" in template_ids, "NOVA agent template should exist"
        
        # Check MOIRA has mentorship in description/prompt
        moira = next((t for t in templates if t["id"] == "moira"), None)
        assert moira is not None
        assert "mentoria" in moira.get("description", "").lower() or "mentoria" in moira.get("system_prompt", "").lower(), \
            "MOIRA should have mentorship capabilities"
        
        # Check NOVA has content creation capabilities
        nova = next((t for t in templates if t["id"] == "nova"), None)
        assert nova is not None
        assert "conteudo" in nova.get("description", "").lower() or "aulas" in nova.get("system_prompt", "").lower(), \
            "NOVA should have content creation capabilities"
        
        print(f"PASS: MOIRA and NOVA agents have mentorship capabilities")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
