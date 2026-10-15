"""Exercise accepted commit subjects and rejected missing or invalid trailers."""

import unittest

from check_commit_message import validate

SIGN_OFF = "Signed-off-by: Example Contributor <contributor@example.com>"


class CommitMessageTests(unittest.TestCase):
    def test_conventional_commits_with_signoff(self):
        for subject in (
            "ci: add workflow",
            "fix(sync): handle conflicts",
            "feat!: change input",
        ):
            with self.subTest(subject=subject):
                self.assertEqual(validate(f"{subject}\n\n{SIGN_OFF}\n"), [])

    def test_nonconventional_subjects(self):
        for subject in ("Update workflow", "ci:no space", "ci: ", ""):
            with self.subTest(subject=subject):
                self.assertTrue(validate(f"{subject}\n\n{SIGN_OFF}\n"))

    def test_missing_or_invalid_signoff(self):
        for body in (
            "",
            "Signed-off-by: Contributor",
            "Signed-off-by: Name <no-email>",
        ):
            with self.subTest(body=body):
                self.assertTrue(validate(f"ci: update workflow\n\n{body}\n"))

    def test_signoff_must_be_a_trailer(self):
        message = f"ci: update workflow\n\n{SIGN_OFF}\n\nMore body text.\n"
        self.assertTrue(validate(message))

    def test_signoff_can_follow_other_trailers(self):
        message = f"ci: update workflow\n\nAssisted-by: Codex\n{SIGN_OFF}\n"
        self.assertEqual(validate(message), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
