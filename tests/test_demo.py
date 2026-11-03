import json
from pathlib import Path
import tempfile
import threading
import unittest
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app
import database
from workflows import QUERY


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old_path = database.DB_PATH
        database.DB_PATH = str(Path(cls.tmp.name) / "test.sqlite")
        app.initialize()
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        database.DB_PATH = cls.old_path
        cls.tmp.cleanup()

    def request(self, path, body=None, mode="batched"):
        req = Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                      headers={"Content-Type": "application/json", "X-Resolver-Mode": mode})
        with urlopen(req) as response:
            return json.load(response), int(response.headers["X-SQL-Queries"])

    def test_same_view_and_nplus1(self):
        users, _ = self.request("/api/v1/users")
        expected = []
        for user in users:
            orders, _ = self.request(f'/api/v1/users/{user["id"]}/orders')
            expected.append({"name": user["name"], "orders": [
                {"product": o["product"], "total_cents": o["total_cents"]} for o in orders]})
        naive, naive_count = self.request("/graphql", {"query": QUERY}, "naive")
        batched, batched_count = self.request("/graphql", {"query": QUERY})
        self.assertEqual(naive["data"], batched["data"])
        self.assertEqual(batched["data"]["users"], expected)
        self.assertEqual(naive_count, 1 + len(users))
        self.assertEqual(batched_count, 2)

    def test_validation_does_not_query_database(self):
        result, count = self.request("/graphql", {"query": "{ users { password } }"})
        self.assertTrue(result["errors"])
        self.assertEqual(count, 0)

    def test_variables_and_only_requested_fields(self):
        result, count = self.request("/graphql", {
            "query": "query One($id: ID!) { user(id: $id) { name } }", "variables": {"id": "1"}})
        self.assertEqual(result["data"], {"user": {"name": "Ana"}})
        self.assertEqual(count, 1)

    def test_aliases_use_request_scoped_batch(self):
        result, count = self.request("/graphql", {"query": '{ a: user(id: "1") { orders { id } } b: user(id: "2") { orders { id } } }'})
        self.assertEqual(len(result["data"]["a"]["orders"]), 2)
        self.assertEqual(len(result["data"]["b"]["orders"]), 1)
        self.assertEqual(count, 3)

    def test_rest_aggregate_and_missing_user(self):
        result, count = self.request("/api/v1/users-with-orders")
        self.assertEqual(sum(len(u["orders"]) for u in result), 4)
        self.assertEqual(count, 2)
        with self.assertRaises(HTTPError) as exc:
            self.request("/api/v1/users/999")
        self.assertEqual(exc.exception.code, 404)

    def test_bad_json_structure(self):
        with self.assertRaises(HTTPError) as exc:
            self.request("/graphql", ["not an object"])
        self.assertEqual(exc.exception.code, 400)

    def test_seed_is_idempotent(self):
        app.initialize()
        users, _ = self.request("/api/v1/users")
        self.assertEqual(len(users), 3)

    def test_terminal_demo_all(self):
        result = subprocess.run(
            [sys.executable, "demo.py", "all", "--base", self.base],
            capture_output=True, text=True, encoding="utf-8", timeout=20,
            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(result.returncode, 0, result.stderr)
        for label in ("REST", "OVERFETCH", "GRAPHQL", "NPLUS1", "ERROR"):
            self.assertIn(label, result.stdout)
        self.assertIn("4 requests HTTP", result.stdout)

    def test_subcommands_are_independent(self):
        for command in ("rest", "overfetch", "graphql", "nplus1", "error"):
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, "demo.py", command, "--base", self.base],
                    capture_output=True, text=True, encoding="utf-8", timeout=20,
                    env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("TOTAL:", result.stdout)
                self.assertIn("1.", result.stdout)

    def test_unknown_routes_and_invalid_mode(self):
        for path, body, mode, expected in [
            ("/unknown", None, "batched", 404),
            ("/api/v1/users/no/orders", None, "batched", 404),
            ("/api/v1/users/999/orders", None, "batched", 404),
            ("/graphql", {"query": QUERY}, "invalid", 400),
        ]:
            with self.subTest(path=path, mode=mode):
                with self.assertRaises(HTTPError) as exc:
                    self.request(path, body, mode)
                self.assertEqual(exc.exception.code, expected)

    def test_concurrent_modes_do_not_change_other_requests(self):
        modes = ["naive", "batched"] * 4

        def execute(mode):
            return mode, self.request("/graphql", {"query": QUERY}, mode)

        with ThreadPoolExecutor(max_workers=4) as pool:
            for mode, (body, count) in pool.map(execute, modes):
                self.assertEqual(body["extensions"]["resolverMode"], mode)
                self.assertEqual(count, {"naive": 4, "batched": 2}[mode])

    def test_compact_display_preserves_received_size(self):
        outputs = []
        for flags in ([], ["--full"]):
            result = subprocess.run(
                [sys.executable, "demo.py", "overfetch", "--base", self.base, *flags],
                capture_output=True, text=True, encoding="utf-8", timeout=20,
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(result.stdout)
        summaries = [next(line for line in out.splitlines() if line.startswith("TOTAL:"))
                     for out in outputs]
        self.assertEqual(summaries[0], summaries[1])
        self.assertLess(len(outputs[0]), len(outputs[1]))


if __name__ == "__main__":
    unittest.main()
