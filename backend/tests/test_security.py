import os
import sqlite3
import tempfile
import unittest

os.environ["SPICE_DB"] = os.path.join(tempfile.mkdtemp(), "security.db")

from fastapi.testclient import TestClient  # noqa: E402
from app import db, main  # noqa: E402
from app.main import app  # noqa: E402
from app import pipeline  # noqa: E402


class SecurityApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = TestClient(app)
        cls.c = cls.ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__(None, None, None)

    def register(self, name, pw="goodpass1"):
        return self.c.post("/api/auth/register", json={"username": name, "password": pw})

    def login(self, name, pw):
        return self.c.post("/api/auth/login", json={"username": name, "password": pw})

    # ---- passwords -----------------------------------------------------------
    def test_weak_passwords_rejected(self):
        for pw in ("short1", "alllettersonly", "12345678", "password123"):
            r = self.register("weak_" + str(abs(hash(pw)) % 1000), pw)
            self.assertEqual(r.status_code, 422, pw)

    def test_strong_password_accepted_and_stored_as_hash(self):
        self.assertEqual(self.register("strong1").status_code, 200)
        row = sqlite3.connect(db.DB_PATH).execute(
            "SELECT password_hash FROM users WHERE username='strong1'").fetchone()
        self.assertTrue(row[0].startswith("pbkdf2_sha256$600000$"))
        self.assertNotIn("goodpass1", row[0])

    def test_legacy_password_hash_still_verifies(self):
        salt = "ab" * 16
        legacy = db._pbkdf2("oldpass99", salt, 200_000)
        self.assertTrue(db.verify_password("oldpass99", salt, legacy))
        self.assertFalse(db.verify_password("wrong", salt, legacy))

    # ---- sessions ------------------------------------------------------------
    def test_session_tokens_are_stored_hashed(self):
        token = self.register("hashed1").json()["token"]
        rows = sqlite3.connect(db.DB_PATH).execute("SELECT token FROM sessions").fetchall()
        self.assertNotIn(token, [r[0] for r in rows])
        self.assertEqual(self.c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code, 200)

    def test_expired_session_is_rejected(self):
        token = self.register("expire1").json()["token"]
        auth = {"Authorization": f"Bearer {token}"}
        old = db._cutoff(db.SESSION_HOURS * 3600 + 60)
        with sqlite3.connect(db.DB_PATH) as conn:
            conn.execute("UPDATE sessions SET created_at = ? WHERE token = ?", (old, db._token_hash(token)))
        self.assertEqual(self.c.get("/api/auth/me", headers=auth).status_code, 401)

    def test_logout_invalidates_token(self):
        token = self.register("logout1").json()["token"]
        auth = {"Authorization": f"Bearer {token}"}
        self.assertEqual(self.c.post("/api/auth/logout", headers=auth).status_code, 200)
        self.assertEqual(self.c.get("/api/auth/me", headers=auth).status_code, 401)

    # ---- brute force ---------------------------------------------------------
    def test_lockout_after_repeated_failures(self):
        self.register("target1")
        for _ in range(db.MAX_FAILED_LOGINS - 1):
            self.assertEqual(self.login("target1", "wrongpass1").status_code, 401)
        r = self.login("target1", "wrongpass1")           # the failure that trips the lock
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r.headers)
        self.assertEqual(self.login("target1", "goodpass1").status_code, 429)   # even the right password

    def test_success_clears_failure_count(self):
        self.register("forgetful1")
        for _ in range(db.MAX_FAILED_LOGINS - 2):
            self.login("forgetful1", "wrongpass1")
        self.assertEqual(self.login("forgetful1", "goodpass1").status_code, 200)
        for _ in range(db.MAX_FAILED_LOGINS - 1):
            self.assertEqual(self.login("forgetful1", "wrongpass1").status_code, 401)

    def test_unknown_usernames_get_the_same_treatment(self):
        for _ in range(db.MAX_FAILED_LOGINS - 1):
            self.assertEqual(self.login("nobody_here", "wrongpass1").status_code, 401)
        self.assertEqual(self.login("nobody_here", "wrongpass1").status_code, 429)

    # ---- headers, limits, access ----------------------------------------------
    def test_security_headers(self):
        r = self.c.get("/api/grammar")
        self.assertEqual(r.headers["x-content-type-options"], "nosniff")
        self.assertEqual(r.headers["x-frame-options"], "DENY")
        self.assertEqual(r.headers["cache-control"], "no-store")
        self.assertIn("default-src 'none'", r.headers["content-security-policy"])

    def test_cors_only_allows_the_app_origin(self):
        ok = self.c.options("/api/lex", headers={"Origin": "http://localhost:5173",
                                                 "Access-Control-Request-Method": "POST"})
        bad = self.c.options("/api/lex", headers={"Origin": "http://evil.example",
                                                  "Access-Control-Request-Method": "POST"})
        self.assertEqual(ok.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertIsNone(bad.headers.get("access-control-allow-origin"))

    def test_rate_limit(self):
        token = self.register("busy1").json()["token"]
        auth = {"Authorization": f"Bearer {token}"}
        old = main.RATE_LIMIT
        main.RATE_LIMIT = 5
        try:
            codes = [self.c.post("/api/lex", json={"source": "plate"}, headers=auth).status_code for _ in range(7)]
        finally:
            main.RATE_LIMIT = old
        self.assertEqual(codes[:5], [200] * 5)
        self.assertEqual(codes[5:], [429, 429])

    def test_oversized_source_rejected(self):
        token = self.register("big1").json()["token"]
        r = self.c.post("/api/lex", json={"source": "x" * 60_000}, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(r.status_code, 422)

    def test_other_users_logs_are_private(self):
        a = self.register("owner1").json()["token"]
        b = self.register("snoop1").json()["token"]
        self.c.post("/api/lex", json={"source": "serve 1\nplate"}, headers={"Authorization": f"Bearer {a}"})
        self.assertEqual(self.c.get("/api/logs?all=true", headers={"Authorization": f"Bearer {b}"}).status_code, 403)
        mine = self.c.get("/api/logs", headers={"Authorization": f"Bearer {b}"}).json()
        self.assertTrue(all(row["username"] == "snoop1" for row in mine))

    def test_sql_injection_in_username_is_just_text(self):
        r = self.c.post("/api/auth/login", json={"username": "x' OR '1'='1", "password": "whatever1"})
        self.assertEqual(r.status_code, 422)   # not even a valid username


class HostileProgramTests(unittest.TestCase):
    """Programs written to crash or exhaust the compiler must end quickly with a clear error."""

    def run_all(self, src):
        return pipeline.run_all(src)

    def test_huge_number_literal(self):
        r = self.run_all("serve " + "9" * 5000 + "\nplate")
        self.assertEqual(r["stopped_at"], "lexical")

    def test_number_squaring_loop(self):
        r = self.run_all("mix x into 99999\nsimmer 1 hotter 0\n x into x blend x\ndone\nplate")
        self.assertEqual(r["errors"][0]["message"], "Number is too large (limit 1e30)")

    def test_string_doubling_loop(self):
        r = self.run_all('mix s into "aaaa"\nsimmer 1 hotter 0\n s into s plus s\ndone\nplate')
        self.assertIn("Text is too long", r["errors"][0]["message"])

    def test_output_flood(self):
        r = self.run_all('simmer 1 hotter 0\n serve "x"\ndone\nplate')
        self.assertIn("Output limit", r["errors"][0]["message"])

    def test_deep_nesting(self):
        r = self.run_all("taste 1\n" * 1500 + "done\n" * 1500 + "plate")
        self.assertEqual(r["stopped_at"], "syntax")
        self.assertTrue(any("nested too deeply" in e["message"] for e in r["errors"]))

    def test_very_long_expression(self):
        r = self.run_all("serve " + " plus ".join(["1"] * 9000) + "\nplate")
        self.assertTrue(any("Expression is too long" in e["message"] for e in r["errors"]))

    def test_error_flood_is_capped(self):
        r = self.run_all("serve\n" * 5000 + "plate")
        self.assertLessEqual(len(r["errors"]), 101)

    def test_normal_programs_unaffected(self):
        r = self.run_all("mix x into 1000000\nserve x blend x\nplate")
        self.assertTrue(r["ok"])
        self.assertEqual(r["output"], ["1000000000000"])


if __name__ == "__main__":
    unittest.main()
