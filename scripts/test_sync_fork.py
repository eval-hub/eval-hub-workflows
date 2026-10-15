"""Offline smoke tests for the Bash step in the reusable fork-sync workflow."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/sync-fork.yml"


class ForkSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for executable in ("bash", "jq"):
            if not shutil.which(executable):
                raise RuntimeError(
                    f"Install {executable} before running workflow tests"
                )
        workflow = yaml.safe_load(WORKFLOW.read_text())
        steps = workflow["jobs"]["sync"]["steps"]
        cls.script = next(
            step["run"] for step in steps if step["name"] == "Sync destination fork"
        )

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="fork-sync-test-")
        self.addCleanup(self.directory.cleanup)
        self.tmp = Path(self.directory.name)
        self.arguments = self.tmp / "arguments.json"
        self.summary = self.tmp / "summary.md"
        mock_gh = self.tmp / "gh"
        mock_gh.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['MOCK_ARGUMENTS']).write_text(json.dumps(sys.argv[1:]))\n"
            "if os.environ['MOCK_STATUS'] != '200':\n"
            "    print('mock HTTP ' + os.environ['MOCK_STATUS'], file=sys.stderr)\n"
            "    sys.exit(1)\n"
            "print(os.environ['MOCK_RESPONSE'])\n"
        )
        mock_gh.chmod(0o755)
        self.response = {
            "message": "Successfully fetched and fast-forwarded from upstream",
            "merge_type": "fast-forward",
            "base_branch": "eval-hub:main",
        }
        self.env = dict(
            os.environ,
            PATH=str(self.tmp) + os.pathsep + os.environ["PATH"],
            GH_TOKEN="test-token",
            GH_HOST="github.com",
            TARGET_REPOSITORY="opendatahub-io/eval-hub",
            TARGET_BRANCH="main",
            RUNNER_TEMP=str(self.tmp),
            GITHUB_STEP_SUMMARY=str(self.summary),
            MOCK_ARGUMENTS=str(self.arguments),
            MOCK_STATUS="200",
        )

    def run_sync(self, **overrides):
        env = dict(self.env, MOCK_RESPONSE=json.dumps(self.response), **overrides)
        return subprocess.run(
            ["bash", "-c", self.script],
            cwd=self.tmp,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def assert_api_request(self, repository="opendatahub-io/eval-hub", branch="main"):
        self.assertEqual(
            json.loads(self.arguments.read_text()),
            [
                "api",
                "--method",
                "POST",
                f"repos/{repository}/merge-upstream",
                "-H",
                "Accept: application/vnd.github+json",
                "-H",
                "X-GitHub-Api-Version: 2022-11-28",
                "-f",
                f"branch={branch}",
            ],
        )

    def test_bash_syntax(self):
        result = subprocess.run(
            ["bash", "-n"],
            input=self.script,
            text=True,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_successful_results(self):
        for merge_type, message in (
            ("fast-forward", "Successfully fetched and fast-forwarded from upstream"),
            ("merge", "Successfully merged from upstream"),
            ("none", "Already up to date"),
        ):
            with self.subTest(merge_type=merge_type):
                self.summary.unlink(missing_ok=True)
                self.response.update(merge_type=merge_type, message=message)
                result = self.run_sync()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assert_api_request()
                self.assertEqual(
                    self.summary.read_text(),
                    f"### Fork synchronization\n{message}\n"
                    f"Merge type: {merge_type}\nUpstream branch: eval-hub:main\n",
                )

    def test_api_failures_fail_the_step(self):
        for status in ("409", "403", "422"):
            with self.subTest(status=status):
                result = self.run_sync(MOCK_STATUS=status)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("::error::Fork sync failed", result.stdout)
                self.assertIn(status, result.stderr)
                self.assert_api_request()
                self.assertFalse(self.summary.exists())

    def test_invalid_inputs_do_not_call_api(self):
        for overrides in (
            {"TARGET_REPOSITORY": "../bad/repository"},
            {"TARGET_REPOSITORY": "owner/repo?extra=value"},
            {"TARGET_BRANCH": ""},
            {"GH_TOKEN": ""},
        ):
            with self.subTest(overrides=overrides):
                result = self.run_sync(**overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("::error::", result.stdout)
                self.assertFalse(self.arguments.exists())
                self.assertFalse(self.summary.exists())

    def test_custom_destination_and_branch(self):
        result = self.run_sync(
            TARGET_REPOSITORY="another/fork", TARGET_BRANCH="release/v1"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_api_request(repository="another/fork", branch="release/v1")

    def test_branch_is_passed_literally(self):
        branch = "feature/$(touch injected);`touch injected-too`"
        result = self.run_sync(TARGET_BRANCH=branch)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_api_request(branch=branch)
        self.assertFalse((self.tmp / "injected").exists())
        self.assertFalse((self.tmp / "injected-too").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
