"""Offline regression checks for the external-evaluator issue privacy boundary."""

import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import canary


class IssuePrivacyTests(unittest.TestCase):
    def test_discovery_never_requests_or_retains_issue_bodies(self):
        marker = "CONFIDENTIAL_BODY_DO_NOT_SEND"
        issue = {
            "number": 7,
            "title": "Fix a harmless edge case",
            "url": "https://github.com/example/repo/issues/7",
            "labels": [{"name": "bug"}],
            "body": marker,  # Deliberately returned despite the requested field list.
        }
        with mock.patch.object(canary, "command", return_value=json.dumps([issue])) as run:
            candidates = canary.discover({"allowed_repositories": ["example/repo"]})
        self.assertEqual(len(candidates), 1)
        self.assertNotIn("body", candidates[0])
        self.assertNotIn(marker, json.dumps(candidates))
        argv = run.call_args.args[0]
        self.assertEqual(argv[argv.index("--json") + 1], "number,title,url,labels")

    def test_plan_drops_unexpected_body_before_external_agent(self):
        marker = "CONFIDENTIAL_BODY_DO_NOT_SEND"
        issue = {
            "repo": "example/repo",
            "number": 7,
            "title": "Fix a harmless edge case",
            "url": "https://github.com/example/repo/issues/7",
            "labels": ["bug"],
            "body": marker,  # Simulates a future collector regression.
        }
        prompts = []

        def evaluate(prompt):
            prompts.append(prompt)
            return json.dumps({
                "issue_url": issue["url"],
                "task": "Add a small regression test for the reported edge case.",
                "acceptance": ["The test reproduces the issue", "The test passes"],
                "rationale": "A bounded issue exists",
            })

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(canary, "RUNS", Path(tmp)), \
                 mock.patch.object(canary, "config", return_value={"max_candidates": 12}), \
                 mock.patch.object(canary, "discover", return_value=[issue]), \
                 mock.patch.object(canary, "external_agent", side_effect=evaluate):
                canary.plan(argparse.Namespace(send=False))
            saved = json.loads(next(Path(tmp).glob("*/run.json")).read_text(encoding="utf-8"))

        self.assertEqual(len(prompts), 1)
        self.assertNotIn(marker, prompts[0])
        self.assertNotIn(marker, json.dumps(saved))
        self.assertEqual(saved["source"], "issues")


if __name__ == "__main__":
    unittest.main()
