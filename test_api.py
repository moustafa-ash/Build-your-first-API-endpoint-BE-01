import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import main


class TaskApiTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        main.DATABASE_PATH = Path(self.tempdir.name) / "tasks.db"
        main.initialize_database()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        self.tempdir.cleanup()

    def test_crud_validation_and_persistence(self):
        self.assertEqual(len(self.client.get("/tasks").json()), 3)
        main.initialize_database()
        self.assertEqual(len(self.client.get("/tasks").json()), 3)
        self.assertEqual(self.client.get("/tasks/999").json(), {"error": "Task not found"})
        self.assertEqual(self.client.get("/tasks/999").status_code, 404)
        self.assertEqual(self.client.post("/tasks", json={}).status_code, 400)
        self.assertEqual(self.client.post("/tasks", json={"title": "  "}).status_code, 400)

        created = self.client.post("/tasks", json={"title": "Persist me"})
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["id"]
        self.client.close()
        self.client = TestClient(main.app)
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
