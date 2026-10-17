"""Exercise content selection, failed updates and byte-preserving profile replacement."""

import base64
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("sync_projects", Path(__file__).resolve().parents[1] / "scripts/sync_projects.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
SOURCE = """<!-- SHARED:START -->
# Example

Python · Manim
<!-- SHARED:END -->

<!-- WEBPAGE:START -->
Website-only detailed explanation.
<!-- WEBPAGE:END -->

<!-- PANOPEPINO:START -->
Profile-only short summary.
<!-- PANOPEPINO:END -->
"""


class ProfileSyncTests(unittest.TestCase):
    """Verify generation failure leaves existing profile content untouched."""

    def test_destination_sections_are_distinct(self):
        parsed = sync.parse_source(SOURCE)
        self.assertEqual(parsed["title"], "Example")
        self.assertEqual(parsed["tags"], ["Python", "Manim"])
        self.assertNotIn("Website-only", parsed["PANOPEPINO"])

    def test_bad_source_markers_fail(self):
        for source in (SOURCE.replace("<!-- WEBPAGE:END -->", ""), SOURCE + SOURCE, SOURCE + "extra"):
            with self.subTest(source=source[:40]), self.assertRaises(ValueError):
                sync.parse_source(source)

    def test_html_and_unsafe_links_fail(self):
        for text in ("<script>alert(1)</script>", "[bad](javascript:alert)"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                sync.parse_source(SOURCE.replace("Profile-only short summary.", text))

    def test_outside_readme_bytes_are_preserved(self):
        original = "Outside é\r\n" + sync.START + "\nOld\n" + sync.END + "\r\nTail 🐍"
        updated = sync.replace_section(original, "New")
        self.assertEqual(updated.split(sync.START)[0].encode(), original.split(sync.START)[0].encode())
        self.assertEqual(updated.split(sync.END)[1].encode(), original.split(sync.END)[1].encode())
        self.assertEqual(sync.replace_section(updated, "New"), updated)

    def test_missing_duplicate_and_reversed_readme_markers_fail(self):
        for text in ("No markers", sync.START + sync.START + sync.END, sync.END + sync.START):
            with self.subTest(text=text), self.assertRaises(ValueError):
                sync.replace_section(text, "New")

    def test_nested_render_uses_only_profile_copy(self):
        entries = [{"id": "group", "local": "unused", "components": [{"id": "child", "local": "unused"}]}]
        with patch.object(sync, "load_source", return_value=sync.parse_source(SOURCE)):
            result = sync.render_projects(entries)
        self.assertIn("### Example", result)
        self.assertIn("#### Example", result)
        self.assertNotIn("Website-only", result)

    def test_duplicate_ids_fail(self):
        with patch.object(sync, "load_source", return_value=sync.parse_source(SOURCE)):
            with self.assertRaises(ValueError):
                sync.render_projects([{"id": "same"}, {"id": "same"}])

    def test_remote_reads_resolved_commit_and_logs_revision(self):
        responses = [
            {"private": False, "default_branch": "main"},
            {"sha": "a" * 40},
            {"content": base64.b64encode(SOURCE.encode()).decode()},
        ]
        entry = {"repository": "PanoPepino/example"}
        with patch.object(sync, "api_json", side_effect=responses) as api:
            source = sync.load_source(entry, True, None, {})
        self.assertEqual(source["title"], "Example")
        self.assertIn("?ref=" + "a" * 40, api.call_args.args[0])

    def test_private_remote_is_rejected(self):
        with patch.object(sync, "api_json", return_value={"private": True}):
            with self.assertRaises(ValueError):
                sync.load_source({"repository": "PanoPepino/example"}, True, None, {})

    def test_failed_fetch_and_check_mode_do_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "content").mkdir()
            registry = {"version": 1, "projects": [{"id": "example", "repository": "PanoPepino/example"}]}
            (root / "content/projects.json").write_text(json.dumps(registry))
            target = root / "README.md"
            target.write_text(sync.START + "\nOld\n" + sync.END)
            original = target.read_bytes()
            for arguments, failure in ((["sync", "--remote"], OSError("failed fetch")), (["sync", "--check"], None)):
                with patch.object(sync, "ROOT", root), patch.object(sys, "argv", arguments):
                    if failure:
                        with patch.object(sync, "load_source", side_effect=failure), self.assertRaises(OSError):
                            sync.main()
                    else:
                        with patch.object(sync, "load_source", return_value=sync.parse_source(SOURCE)), self.assertRaises(ValueError):
                            sync.main()
                self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
