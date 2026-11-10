"""Dependabot merges must use the dedicated App without release authority."""

import json
import os
import subprocess
import textwrap
import unittest
from pathlib import Path


class DependabotPolicyTests(unittest.TestCase):
    def test_complete_ci_gate_executes_its_result_policy(self):
        root = Path(__file__).resolve().parents[1]
        workflows = [
            path.read_text()
            for path in (root / ".github/workflows").glob("*")
            if path.is_file() and "dependency-validation:" in path.read_text()
        ]
        self.assertEqual(len(workflows), 1)
        script = textwrap.dedent(
            workflows[0].split("node <<'NODE'\n", 1)[1].split("          NODE", 1)[0]
        )
        cases = [
            ({"test": {"result": "success"}}, True),
            ({"test": {"result": "success"}, "publish": {"result": "skipped"}}, True),
            ({"test": {"result": "failure"}}, False),
            ({"test": {"result": "cancelled"}}, False),
            ({"test": {"result": "skipped"}}, False),
            ({}, False),
        ]
        for jobs, succeeds in cases:
            with self.subTest(jobs=jobs):
                result = subprocess.run(
                    ["node", "-e", script],
                    env=dict(os.environ, CI_RESULTS=json.dumps(jobs)),
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode == 0, succeeds)

    def test_dedicated_merge_identity(self):
        root = Path(__file__).resolve().parents[1]
        path = root / ".github/workflows/dependabot-merge.yml"
        self.assertTrue(path.exists(), "A trusted completed-CI handler is required")
        workflow = path.read_text()
        self.assertNotIn("secrets.RELEASE_WRITER_APP_", workflow)
        self.assertIn("app-id: ${{ secrets.RELEASE_MERGER_APP_ID }}", workflow)
        self.assertIn("private-key: ${{ secrets.RELEASE_MERGER_APP_KEY }}", workflow)
        action = workflow.split("merge-tested-dependabot@", 1)[1]
        self.assertIn("app-id: ${{ secrets.RELEASE_MERGER_APP_ID }}", action)
        self.assertIn("workflow_run:", workflow)
        self.assertNotIn("pull_request_target:", workflow)


if __name__ == "__main__":
    unittest.main()
