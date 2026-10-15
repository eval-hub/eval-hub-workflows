"""Check immutable references in workflows and composite actions."""

import unittest

from check_action_pins import check_references


class ActionPinTests(unittest.TestCase):
    def test_accepts_immutable_and_local_actions(self):
        for reference in (
            "actions/checkout@" + "a" * 40,
            "owner/repo/path/to/action@" + "b" * 40,
            "owner/repo/.github/workflows/test.yml@" + "c" * 40,
            "./.github/actions/local",
            "docker://alpine@sha256:" + "d" * 64,
        ):
            with self.subTest(reference=reference):
                self.assertEqual(check_references({"uses": reference}), [])

    def test_rejects_mutable_or_malformed_references(self):
        for reference in (
            "actions/checkout@v6",
            "owner/repo@main",
            "owner/repo@abc1234",
            "owner/repo@" + "z" * 40,
            "docker://alpine:latest",
            "docker://alpine@sha256:abc1234",
            None,
        ):
            with self.subTest(reference=reference):
                self.assertTrue(check_references({"uses": reference}))

    def test_checks_job_and_step_references(self):
        workflow = {
            "jobs": {
                "reusable": {"uses": "owner/repo/.github/workflows/test.yml@main"},
                "local": {"steps": [{"uses": "actions/checkout@v6"}]},
            }
        }
        errors = check_references(workflow)
        self.assertEqual(len(errors), 2)
        self.assertIn("jobs.reusable.uses", errors[0])
        self.assertIn("jobs.local.steps[0].uses", errors[1])

    def test_checks_composite_actions(self):
        action = {"runs": {"using": "composite", "steps": [{"uses": "owner/repo@v1"}]}}
        self.assertTrue(check_references(action))


if __name__ == "__main__":
    unittest.main(verbosity=2)
