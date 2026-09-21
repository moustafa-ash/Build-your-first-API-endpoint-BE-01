import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

import database
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


if __name__ == "__main__":
    unittest.main()
