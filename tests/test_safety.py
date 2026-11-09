"""Offline safety regressions: no GitHub, Codex, Courier, or ORC required."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import canary


class CanarySafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runs = Path(self.tmp.name) / "runs"
        self.runs.mkdir()
        self.run_id = "safe-run_01"
        self.folder = self.runs / self.run_id
        self.folder.mkdir()
        self.record = {
            "status": "planned",
            "repo": "NaNIsaac/example",
            "issue_url": "https://github.com/NaNIsaac/example/issues/1",
            "task": "Review a small, testable code change",
            "sent_at": None,
        }
        (self.folder / "run.json").write_text(json.dumps(self.record), encoding="utf-8")
        root_patch = patch.object(canary, "RUNS", self.runs)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def test_dispatch_without_send_is_preview_only(self):
        with patch.object(canary, "config", return_value={"orc_target": "secretary"}), \
             patch.object(canary, "command", side_effect=AssertionError("external command invoked")), \
             contextlib.redirect_stdout(io.StringIO()) as stdout:
            canary.dispatch_id(self.run_id, False)
        self.assertIn("DRY RUN", stdout.getvalue())
        self.assertEqual(json.loads((self.folder / "run.json").read_text(encoding="utf-8")), self.record)

    def test_explicit_send_fails_closed_on_failed_health_check(self):
        with patch.object(canary, "config", return_value={"orc_target": "secretary"}), \
             patch.object(canary, "command", side_effect=RuntimeError("courier unavailable")) as cmd:
            with self.assertRaisesRegex(RuntimeError, "courier unavailable"):
                canary.dispatch_id(self.run_id, True)
        cmd.assert_called_once_with(["courier", "doctor"], timeout=25)
        self.assertEqual(json.loads((self.folder / "run.json").read_text(encoding="utf-8"))["status"], "planned")

    def test_send_updates_record_only_after_receipt(self):
        with patch.object(canary, "config", return_value={"orc_target": "secretary"}), \
             patch.object(canary, "command", side_effect=["health ok", "receipt-123"]) as cmd, \
             contextlib.redirect_stdout(io.StringIO()):
            canary.dispatch_id(self.run_id, True)
        self.assertEqual(cmd.call_count, 2)
        self.assertEqual(cmd.call_args_list[1].args[0][:3], ["courier", "send", "secretary"])
        rec = json.loads((self.folder / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["status"], "dispatched")
        self.assertEqual(rec["courier_receipt"], "receipt-123")
        self.assertIsNotNone(rec["sent_at"])

    def test_run_id_rejects_path_traversal(self):
        for value in ("../safe-run_01", "a/b", "..", "."):
            with self.subTest(run_id=value), self.assertRaises(ValueError):
                canary.load_run(value)

    def test_missing_run_is_rejected(self):
        with self.assertRaises(ValueError):
            canary.load_run("not-found")

    def test_existing_non_planned_run_cannot_be_dispatched(self):
        rec = dict(self.record, status="dispatched")
        (self.folder / "run.json").write_text(json.dumps(rec), encoding="utf-8")
        with patch.object(canary, "config", return_value={}), \
             patch.object(canary, "command", side_effect=AssertionError("external command invoked")):
            with self.assertRaisesRegex(RuntimeError, "not in planned"):
                canary.dispatch_id(self.run_id, True)


if __name__ == "__main__":
    unittest.main()
