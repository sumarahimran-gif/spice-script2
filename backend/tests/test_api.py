import os
import tempfile
import unittest

os.environ["SPICE_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = TestClient(app)
        cls.client = cls.ctx.__enter__()   # runs startup (creates tables)

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__(None, None, None)

    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_flow(self):
        c = self.client
        # lexing requires login
        self.assertEqual(c.post("/api/lex", json={"source": "plate"}).status_code, 401)

        # first user is admin, second is a normal user
        a = c.post("/api/auth/register", json={"username": "admin1", "password": "secret123"}).json()
        b = c.post("/api/auth/register", json={"username": "alice", "password": "secret234"}).json()
        self.assertEqual(a["user"]["role"], "admin")
        self.assertEqual(b["user"]["role"], "user")
        self.assertEqual(c.post("/api/auth/register", json={"username": "alice", "password": "secret234"}).status_code, 409)

        # bad login
        self.assertEqual(c.post("/api/auth/login", json={"username": "alice", "password": "wrongpw99"}).status_code, 401)

        # run lexer + a stub stage as alice
        r = c.post("/api/lex", json={"source": "mix x into 10\nplate"}, headers=self.auth(b["token"]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        r = c.post("/api/lex", json={"source": "mix x into @"}, headers=self.auth(b["token"]))
        self.assertFalse(r.json()["ok"])
        r = c.post("/api/parse", json={"source": "plate"}, headers=self.auth(b["token"]))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        r = c.post("/api/semantic", json={"source": "mix a into 1\nplate"}, headers=self.auth(b["token"]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["symbol_table"][0]["name"], "a")
        r = c.post("/api/icg", json={"source": "mix a into 1\nserve a\nplate"}, headers=self.auth(b["token"]))
        self.assertEqual(r.json()["instruction_count"], 2)
        r = c.post("/api/run", json={"source": "mix a into 2\nserve a blend 3\nplate"}, headers=self.auth(b["token"]))
        self.assertEqual(r.json()["output"], ["6"])
        r = c.post("/api/run-all", json={"source": "mix a into 2\nserve a\nplate"}, headers=self.auth(b["token"]))
        self.assertEqual(r.json()["output"], ["2"])
        r = c.post("/api/run-all", json={"source": "serve zz\nplate"}, headers=self.auth(b["token"]))
        self.assertEqual(r.json()["stopped_at"], "semantic")

        # alice sees only her own logs; admin sees everyone's
        mine = c.get("/api/logs", headers=self.auth(b["token"])).json()
        self.assertTrue(all(row["username"] == "alice" for row in mine))
        self.assertEqual(c.get("/api/logs?all=true", headers=self.auth(b["token"])).status_code, 403)
        everyone = c.get("/api/logs?all=true", headers=self.auth(a["token"])).json()
        self.assertTrue({"admin1", "alice"} <= {row["username"] for row in everyone})

        actions = {(row["action"], row["stage"], row["status"]) for row in mine}
        self.assertIn(("run_stage", "lexical", "success"), actions)
        self.assertIn(("run_stage", "lexical", "error"), actions)
        self.assertIn(("run_stage", "syntax", "success"), actions)
        self.assertIn(("run_stage", "semantic", "success"), actions)
        self.assertIn(("run_stage", "icg", "success"), actions)
        self.assertIn(("run_stage", "run", "success"), actions)
        self.assertIn(("run_stage", "full", "success"), actions)
        self.assertIn(("run_stage", "full", "error"), actions)

        # logout invalidates the session
        c.post("/api/auth/logout", headers=self.auth(b["token"]))
        self.assertEqual(c.get("/api/auth/me", headers=self.auth(b["token"])).status_code, 401)

    def test_grammar_public(self):
        g = self.client.get("/api/grammar").json()
        self.assertIn("program", g["ebnf"])
        self.assertTrue(len(g["samples"]) >= 3)


if __name__ == "__main__":
    unittest.main()
