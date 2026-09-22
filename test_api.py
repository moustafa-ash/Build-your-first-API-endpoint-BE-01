import unittest
import os
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

import database
os.environ.setdefault("FLYRANK_SKIP_DB_INIT", "1")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
import main


class TaskApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_database_url = database.DATABASE_URL
        connection_info = conninfo_to_dict(cls.original_database_url)
        cls.test_database = f"tasks_test_{uuid4().hex}"
        admin_info = {**connection_info, "dbname": "postgres"}
        with psycopg.connect(**admin_info, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cls.test_database))
            )

        database.DATABASE_URL = make_conninfo(
            **{**connection_info, "dbname": cls.test_database}
        )
        database.initialize_database()
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        database.DATABASE_URL = cls.original_database_url
        connection_info = conninfo_to_dict(cls.original_database_url)
        with psycopg.connect(
            **{**connection_info, "dbname": "postgres"}, autocommit=True
        ) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(cls.test_database)
                )
            )

    def test_crud_validation_and_persistence(self):
        self.assertEqual(len(self.client.get("/tasks").json()), 3)
        database.initialize_database()
        self.assertEqual(len(self.client.get("/tasks").json()), 3)
        self.assertEqual(self.client.get("/tasks/999").json(), {"error": "Task not found"})
        self.assertEqual(self.client.get("/tasks/999").status_code, 404)
        self.assertEqual(self.client.post("/tasks", json={}).status_code, 400)
        self.assertEqual(self.client.post("/tasks", json={"title": "  "}).status_code, 400)

        created = self.client.post("/tasks", json={"title": "Persist me"})
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["id"]
        self.assertEqual(self.client.get(f"/tasks/{task_id}").json()["title"], "Persist me")

        self.assertEqual(
            self.client.put(f"/tasks/{task_id}", json={"title": "Done", "done": True}).json(),
            {"id": task_id, "title": "Done", "done": True},
        )
        self.assertEqual(self.client.put(f"/tasks/{task_id}", json={"title": "Bad"}).status_code, 400)
        self.assertEqual(self.client.put("/tasks/999", json={"title": "No", "done": False}).status_code, 404)
        self.assertEqual(self.client.delete(f"/tasks/{task_id}").status_code, 204)
        self.assertEqual(self.client.delete(f"/tasks/{task_id}").status_code, 404)
        self.assertEqual(self.client.get(f"/tasks/{task_id}").status_code, 404)


class AuthApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)
        cls.original_auth = main.supabase.auth
        main.supabase.auth = Mock()
        cls.user = SimpleNamespace(
            id="user-123", email="test@example.com", created_at="2026-09-22T00:00:00Z"
        )
        cls.session = SimpleNamespace(access_token="access-token", refresh_token="refresh-token")

    @classmethod
    def tearDownClass(cls):
        main.supabase.auth = cls.original_auth
        cls.client.close()

    def setUp(self):
        main.supabase.auth.reset_mock(side_effect=True)

    def test_signup_and_login_validation_and_success(self):
        main.supabase.auth.sign_up.return_value = SimpleNamespace(user=self.user)
        main.supabase.auth.sign_in_with_password.return_value = SimpleNamespace(session=self.session)

        self.assertEqual(self.client.post("/auth/signup", json={}).status_code, 400)
        signup = self.client.post(
            "/auth/signup", json={"email": " test@example.com ", "password": "password123"}
        )
        self.assertEqual(signup.status_code, 201)
        self.assertEqual(signup.json()["id"], "user-123")

        self.assertEqual(self.client.post("/auth/login", json={"email": "x"}).status_code, 400)
        login = self.client.post(
            "/auth/login", json={"email": "test@example.com", "password": "password123"}
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json(), {"access_token": "access-token", "refresh_token": "refresh-token"})

    def test_invalid_login_and_auth_headers(self):
        main.supabase.auth.sign_in_with_password.side_effect = RuntimeError("invalid")
        invalid_login = self.client.post(
            "/auth/login", json={"email": "test@example.com", "password": "wrong"}
        )
        self.assertEqual(invalid_login.status_code, 401)
        self.assertEqual(invalid_login.json(), {"error": "Invalid login credentials"})

        for header in (None, "Token access-token", "Bearer "):
            headers = {} if header is None else {"Authorization": header}
            response = self.client.get("/protected/profile", headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"error": "Access token required"})

    def test_verified_routes_and_tampered_token(self):
        main.supabase.auth.get_user.return_value = SimpleNamespace(user=self.user)
        headers = {"Authorization": "Bearer access-token"}

        profile = self.client.get("/protected/profile", headers=headers)
        dashboard = self.client.get("/protected/dashboard", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["id"], "user-123")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()["user_id"], "user-123")

        main.supabase.auth.get_user.side_effect = RuntimeError("bad token")
        tampered = self.client.get(
            "/protected/profile", headers={"Authorization": "Bearer tampered"}
        )
        self.assertEqual(tampered.status_code, 401)
        self.assertEqual(tampered.json(), {"error": "Invalid or expired token"})

    @patch("main.httpx.post")
    def test_logout_and_openapi_security(self, post):
        main.supabase.auth.get_user.return_value = SimpleNamespace(user=self.user)
        post.return_value = SimpleNamespace(status_code=204)
        logout = self.client.post(
            "/auth/logout", headers={"Authorization": "Bearer access-token"}
        )
        self.assertEqual(logout.status_code, 204)
        post.assert_called_once()

        paths = main.app.openapi()["paths"]
        self.assertNotIn("security", paths["/public/info"]["get"])
        self.assertEqual(paths["/protected/profile"]["get"]["security"], [{"BearerAuth": []}])
        self.assertEqual(paths["/auth/logout"]["post"]["security"], [{"BearerAuth": []}])


if __name__ == "__main__":
    unittest.main()
