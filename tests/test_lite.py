import io, os, sys, tempfile, unittest
from contextlib import redirect_stdout, redirect_stderr
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json_repair_lite as jr

class T(unittest.TestCase):
    def test_already_valid(self):
        r = jr.repair_one('{"a": 1}')
        self.assertTrue(r["wasValid"])
        self.assertFalse(r["repaired"])
        self.assertEqual(r["value"], {"a": 1})

    def test_trailing_comma_and_quotes(self):
        r = jr.repair_one("{name: 'Ada', ok: true,}")
        self.assertFalse(r["wasValid"])
        self.assertTrue(r["repaired"])
        self.assertEqual(r["value"]["name"], "Ada")
        self.assertTrue(r["value"]["ok"])

    def test_truncated(self):
        r = jr.repair_one('{"items": [1, 2, 3')
        self.assertTrue(r["repaired"])
        self.assertEqual(r["value"]["items"], [1, 2, 3])

    def test_empty(self):
        with self.assertRaises(ValueError):
            jr.repair_one("  ")

    def test_split_single(self):
        docs = jr.split_documents('{"a": 1}', False)
        self.assertEqual(len(docs), 1)

    def test_split_lines(self):
        docs = jr.split_documents('{"a": 1}\n{"b": 2}\n', True)
        self.assertEqual(len(docs), 2)

    def test_repair_text_one(self):
        bundle = jr.repair_text("{name: 'Ada',}")
        self.assertEqual(bundle["count"], 1)
        self.assertEqual(bundle["failed"], 0)
        self.assertEqual(bundle["documents"][0]["value"]["name"], "Ada")

    def test_repair_text_lines(self):
        bundle = jr.repair_text('{"a": 1}\n{b: 2,}', json_lines=True)
        self.assertEqual(bundle["count"], 2)
        self.assertEqual(bundle["failed"], 0)
        self.assertEqual(bundle["documents"][1]["value"]["b"], 2)

    def test_bom(self):
        r = jr.repair_one('\ufeff{"a": 1}')
        self.assertTrue(r["wasValid"])
        self.assertEqual(r["value"], {"a": 1})

    def run_main(self, argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        old = sys.stdin
        sys.stdin = io.StringIO(stdin)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = jr.main(argv)
        finally:
            sys.stdin = old
        return code, out.getvalue(), err.getvalue()

    def test_cli_json_envelope(self):
        code, out, err = self.run_main(["--json"], "{name: 'Ada', ok: true,}")
        self.assertEqual(code, 0)
        self.assertIn('"ok": true', out)
        self.assertIn('"repaired": true', out)
        self.assertIn("Ada", out)
        self.assertNotIn("apify.com", out)

    def test_cli_pretty_valid(self):
        code, out, err = self.run_main([], '{"a": 1}')
        self.assertEqual(code, 0)
        self.assertIn('"a": 1', out)

    def test_cli_json_lines(self):
        code, out, err = self.run_main(["--json-lines"], '{"a": 1}\n{b: 2,}\n')
        self.assertEqual(code, 0)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        self.assertIn('"a": 1', lines[0])
        self.assertIn('"b": 2', lines[1])

    def test_cli_help_has_apify_link(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            jr.main(["--help"])
        self.assertIn("https://apify.com/tidybytetools/json-repair", out.getvalue())

    def test_bad_file(self):
        code, out, err = self.run_main(["--json", "/nope/missing.json"], "")
        self.assertEqual(code, 1)
        self.assertIn('"ok": false', out)

    def test_cli_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "broken.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{name: 'Ada',}")
            code, out, err = self.run_main([path])
            self.assertEqual(code, 0)
            self.assertIn("Ada", out)

    def test_empty_stdin_json(self):
        code, out, err = self.run_main(["--json"], "   ")
        self.assertEqual(code, 1)
        self.assertIn('"ok": false', out)

    def test_version(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as ctx:
            jr.main(["--version"])
        self.assertIn(ctx.exception.code, (0, None))
        self.assertIn("1.0.0", out.getvalue())


if __name__ == "__main__":
    unittest.main()
