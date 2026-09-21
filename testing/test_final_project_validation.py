"""Isolated regression tests for Day 4 final-validation helpers."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("final_validation", ROOT / "python/05_final_project_validation.py")
assert SPEC and SPEC.loader
final_validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(final_validation)


def temporary_directory() -> tempfile.TemporaryDirectory[str]:
    """Keep isolated fixtures in the writable workspace, then remove them."""
    return tempfile.TemporaryDirectory(dir=ROOT / "testing")


class FinalProjectValidationTests(unittest.TestCase):
    @staticmethod
    def write(root: Path, relative: str, contents: str | bytes) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, bytes):
            path.write_bytes(contents)
        else:
            path.write_text(contents, encoding="utf-8")
        return path

    def test_safe_and_conceptual_text_has_no_secret_findings(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            self.write(root, "docs/notes.md", "A token is a concept; secret and password are ordinary documentation words.")
            self.assertEqual(final_validation.scan_secret_findings(root), [])

    def test_fake_secrets_are_reported_without_values(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            github, aws, password = "ghp_" + "a" * 24, "AKIA" + "A" * 16, "synthetic-value-123"
            self.write(root, "config.env", f"github={github}\naws={aws}\npassword = '{password}'\n")
            findings = "\n".join(final_validation.scan_secret_findings(root))
            self.assertIn("github-personal-access-token", findings)
            self.assertIn("aws-access-key", findings)
            self.assertIn("credential-assignment", findings)
            self.assertNotIn(github, findings)
            self.assertNotIn(aws, findings)
            self.assertNotIn(password, findings)

    def test_markdown_image_rules(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            for relative in final_validation.EXPECTED_SCREENSHOTS:
                self.write(root, relative, b"png")
            readme = self.write(root, "README.md", "![Overview](dashboard/screenshots/overview.png \"title\")\n![Product](<dashboard/screenshots/product-seller.png>)\n")
            self.assertEqual(final_validation.parse_markdown_images(readme, root), final_validation.EXPECTED_SCREENSHOTS)

    def test_plain_text_and_invalid_image_destinations_fail(self) -> None:
        cases = {
            "plain": "dashboard/screenshots/overview.png\ndashboard/screenshots/product-seller.png\n",
            "missing": "![One](dashboard/screenshots/overview.png)\n![Two](dashboard/screenshots/missing.png)\n",
            "empty": "![One](dashboard/screenshots/overview.png)\n![Two](dashboard/screenshots/product-seller.png)\n",
            "absolute": "![One](C:/overview.png)\n![Two](dashboard/screenshots/product-seller.png)\n",
            "escape": "![One](../overview.png)\n![Two](dashboard/screenshots/product-seller.png)\n",
            "file": "![One](file:///overview.png)\n![Two](dashboard/screenshots/product-seller.png)\n",
        }
        for name, contents in cases.items():
            with self.subTest(name=name), temporary_directory() as directory:
                root = Path(directory)
                for relative in final_validation.EXPECTED_SCREENSHOTS:
                    self.write(root, relative, b"" if name == "empty" and relative.endswith("product-seller.png") else b"png")
                readme = self.write(root, "README.md", contents)
                with self.assertRaises(AssertionError):
                    final_validation.parse_markdown_images(readme, root)

    def test_claim_disclaimers_pass_and_positive_variants_fail(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            path = self.write(root, "README.md", "Independent portfolio case study; not affiliated with Olist. No interviews were conducted and no real stakeholder access was available.")
            self.assertEqual(final_validation.scan_claim_findings([path], root), [])
            for text in ("An official Olist project.", "I worked with Olist.", "Olist employees advised us.", "Interviews with stakeholders informed requirements.", "Requirements were gathered from real stakeholders.", "Samator"):
                self.write(root, "README.md", text)
                self.assertTrue(final_validation.scan_claim_findings([path], root), text)

    def test_exact_sql_query_identity(self) -> None:
        valid = "\n".join(f"-- QUERY: {name}" for name in sorted(final_validation.EXPECTED_SQL_QUERY_NAMES))
        final_validation.validate_sql_query_labels(valid)
        duplicate = valid.replace("-- QUERY: customer_repeat_order_summary", "-- QUERY: overall_order_fulfillment_summary")
        missing = "\n".join(valid.splitlines()[:-1])
        unexpected = valid.replace("-- QUERY: customer_repeat_order_summary", "-- QUERY: unexpected_query")
        for text in (duplicate, missing, unexpected):
            with self.assertRaises(AssertionError):
                final_validation.validate_sql_query_labels(text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
