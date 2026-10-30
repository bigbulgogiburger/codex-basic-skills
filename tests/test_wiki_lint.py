import hashlib
import importlib.util
from pathlib import Path
import shutil
import unittest
import uuid


SCRIPT = Path(__file__).resolve().parents[1] / "skills/wiki-lint/scripts/wiki_lint.py"
spec = importlib.util.spec_from_file_location("wiki_lint", SCRIPT)
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)


class WikiLintTests(unittest.TestCase):
    def setUp(self):
        # Keep fixtures inside the checkout, including in restricted Windows hosts.
        self.fixture_parent = Path(__file__).resolve().parents[1] / ".test-work"
        self.root = self.fixture_parent / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.wiki = self.root / "wiki"
        self.wiki.mkdir()
        self.write("index.md", "# Index\n[Topic](concepts/topic.md)\n")
        (self.root / "자료").mkdir()
        (self.root / "자료/source.txt").write_text("immutable evidence", encoding="utf-8")
        self.write("concepts/topic.md", self.page("# Topic\n"))

    def tearDown(self):
        if self.root.resolve().parent != self.fixture_parent.resolve():
            raise RuntimeError("fixture cleanup escaped test workspace")
        shutil.rmtree(self.root)

    def write(self, name, text):
        path = self.wiki / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def page(self, body, date="2026-10-30", source="자료/source.txt"):
        return f'---\ntype: concept\nupdated: {date}\nsources: ["{source}"]\n---\n{body}'

    def report(self):
        return lint.inspect(self.wiki, self.root)

    def codes(self):
        return {f["code"] for f in self.report()["findings"]}

    def test_valid_wiki_is_read_only(self):
        def snapshot():
            return {p.relative_to(self.root): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob("*") if p.is_file()}
        before = snapshot()
        self.assertEqual([], self.report()["findings"])
        self.assertEqual(before, snapshot())

    def test_code_examples_are_not_links_or_headings(self):
        self.write("concepts/topic.md", self.page("# Topic\n```md\n# Topic\n[x](missing.md)\n```\n`[x](missing.md)`\n"))
        self.assertEqual(set(), self.codes())

    def test_missing_link_and_self_anchor(self):
        self.write("concepts/topic.md", self.page("# Topic\n[x](missing.md)\n[self](#missing)\n"))
        self.assertEqual({"BROKEN-LINK", "BROKEN-ANCHOR"}, self.codes())

    def test_korean_spaces_parentheses_reference_link(self):
        self.write("concepts/한글 (문서).md", self.page("# 한글 제목\n"))
        self.write("index.md", "# Index\n[Topic](concepts/topic.md)\n[ref][doc]\n\n[doc]: <concepts/한글 (문서).md#한글-제목>\n")
        self.assertEqual(set(), self.codes())

    def test_percent_encoded_path(self):
        self.write("concepts/a b.md", self.page("# A\n"))
        self.write("index.md", "[t](concepts/topic.md)\n[a](concepts/a%20b.md#a)\n")
        self.assertEqual(set(), self.codes())

    def test_duplicate_anchor_collision(self):
        self.write("concepts/topic.md", self.page("# A\n# A\n# A-1\n[ok](#a-1-1)\n"))
        self.assertEqual({"DUP-HEADING"}, self.codes())

    def test_real_calendar_date(self):
        self.write("concepts/topic.md", self.page("# Topic\n", date="2026-02-30"))
        self.assertIn("FRONTMATTER", self.codes())
        self.write("concepts/topic.md", self.page("# Topic\n", date='"2026-02-30"'))
        self.assertIn("FM-DATE", self.codes())

    def test_malformed_yaml_and_type(self):
        self.write("concepts/topic.md", "---\ntype: [\n---\n# Topic\n")
        self.assertIn("FRONTMATTER", self.codes())
        self.write("concepts/topic.md", self.page("# Topic\n").replace("type: concept", "type: [concept]"))
        self.assertIn("FM-TYPE", self.codes())

    def test_missing_source(self):
        self.write("concepts/topic.md", self.page("# Topic\n", source="missing.txt"))
        self.assertIn("MISSING-SOURCE", self.codes())

    def test_orphan_not_suppressed_by_self_link(self):
        self.write("concepts/alone.md", self.page("# Alone\n[self](#alone)\n"))
        self.assertIn("ORPHAN", self.codes())

    def test_unsupported_syntax_is_incomplete(self):
        self.write("concepts/topic.md", self.page("# Topic\n[[unresolved]]\n"))
        self.assertIn("WIKILINK-UNCHECKED", self.codes())
        self.assertEqual(2, lint.exit_code(self.report()))

    def test_invalid_utf8_is_incomplete(self):
        (self.wiki / "unreadable.md").write_bytes(b"\xff\xfe\x00")
        self.assertIn("UNREADABLE", self.codes())
        self.assertEqual(2, lint.exit_code(self.report()))

    def test_no_root_or_empty_wiki_is_not_success(self):
        self.assertEqual(2, lint.exit_code(lint.inspect(self.root / "missing")))
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(2, lint.exit_code(lint.inspect(empty)))

    def test_sources_without_source_root_are_incomplete(self):
        self.assertEqual(2, lint.exit_code(lint.inspect(self.wiki)))

    def test_existing_custom_schema(self):
        self.write("concepts/topic.md", self.page("# Topic\n").replace("type: concept", "type: synthesis"))
        report = lint.inspect(self.wiki, self.root, types=["synthesis"])
        self.assertEqual([], report["findings"])

    def test_boundary_escape_is_not_read(self):
        self.write("concepts/topic.md", self.page("# Topic\n[x](../../../outside.md)\n"))
        self.assertIn("LINK-OUTSIDE-SCOPE", self.codes())


if __name__ == "__main__":
    unittest.main()
