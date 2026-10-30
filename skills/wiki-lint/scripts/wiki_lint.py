#!/usr/bin/env python3
"""Read-only structural checks for a Markdown wiki. See references/checks.md."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

try:
    from markdown_it import MarkdownIt
    import yaml
except ImportError as exc:
    print(f"Missing dependency: {exc.name}; install scripts/requirements.txt", file=sys.stderr)
    sys.exit(2)


def slug(text):
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def parse_page(text):
    """Return metadata, parser tokens and YAML error, preserving original line numbers."""
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
    metadata, error = None, None
    if match:
        try:
            metadata = yaml.safe_load(match.group(1))
            if not isinstance(metadata, dict):
                error = "frontmatter must be a mapping"
        except (yaml.YAMLError, ValueError) as exc:
            error = str(exc).splitlines()[0]
        text = "\n" * match.group(0).count("\n") + text[match.end():]
    elif text.startswith("---\n"):
        error = "unclosed frontmatter"
    return metadata, MarkdownIt().parse(text), error


def heading_ids(tokens):
    result, duplicates = set(), []
    for i, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        children = tokens[i + 1].children or []
        text = "".join(c.content for c in children if c.type in ("text", "code_inline", "image"))
        base, suffix = slug(text), 0
        anchor = base
        while anchor in result:
            suffix += 1
            anchor = f"{base}-{suffix}"
        if suffix:
            duplicates.append((token.map[0] + 1, base))
        result.add(anchor)
    return result, duplicates


def inspect(wiki, source_root=None, hubs=None, types=None, excludes=None):
    wiki = Path(wiki).resolve()
    source_root = Path(source_root).resolve() if source_root else None
    boundary = source_root or wiki.parent
    hubs = set(hubs or ("index.md", "overview.md", "catalog.md", "log.md"))
    types = set(types or ("entity", "concept", "source", "overview", "index", "catalog", "log"))
    excludes = excludes or ("_to_delete", ".git", "__pycache__")
    findings, pages, graph = [], {}, {}

    def add(path, line, code, detail, severity="error"):
        try:
            label = str(Path(path).relative_to(wiki))
        except ValueError:
            label = str(path)
        findings.append(dict(file=label.replace("\\", "/"), line=line, code=code,
                             detail=detail, severity=severity))

    if not wiki.is_dir() or not wiki.is_relative_to(boundary):
        add(wiki, 1, "INVALID-ROOT", "wiki must exist inside source-root", "incomplete")
        return dict(pages=0, findings=findings, semantic_review="not performed")
    for path in sorted(wiki.rglob("*.md")):
        rel = path.relative_to(wiki)
        if any(part in excludes for part in rel.parts):
            continue
        if not path.resolve().is_relative_to(wiki):
            add(path, 1, "OUTSIDE-SCOPE", "symlink target outside wiki", "incomplete")
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            add(path, 1, "UNREADABLE", type(exc).__name__, "incomplete")
            continue
        metadata, tokens, error = parse_page(text)
        anchors, duplicates = heading_ids(tokens)
        pages[path.resolve()] = (metadata, tokens, anchors)
        graph[path.resolve()] = set()
        if error:
            add(path, 1, "FRONTMATTER", error)
        elif metadata is None and rel.as_posix() not in hubs:
            add(path, 1, "FRONTMATTER", "missing frontmatter")
        elif metadata is not None:
            required = ("type", "updated") if rel.as_posix() in hubs else ("type", "updated", "sources")
            for key in required:
                if key not in metadata:
                    add(path, 1, "FM-MISSING", key)
            if "type" in metadata and (not isinstance(metadata["type"], str) or metadata["type"] not in types):
                add(path, 1, "FM-TYPE", str(metadata["type"]))
            if "updated" in metadata:
                value = str(metadata["updated"])
                try:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                        raise ValueError(value)
                    dt.date.fromisoformat(value)
                except ValueError:
                    add(path, 1, "FM-DATE", value)
            if "sources" in metadata:
                sources = metadata["sources"]
                if not isinstance(sources, list) or any(not isinstance(s, str) or not s.strip() for s in sources):
                    add(path, 1, "FM-SOURCES", "sources must be a list of nonempty strings")
                else:
                    if not sources and rel.as_posix() not in hubs:
                        add(path, 1, "NO-SOURCES", "no source references", "warning")
                    for source in sources:
                        if re.match(r"^https?://", source):
                            continue
                        if source_root is None:
                            add(path, 1, "SOURCE-UNCHECKED", source, "incomplete")
                            continue
                        target = (source_root / source).resolve()
                        if not target.is_relative_to(source_root):
                            add(path, 1, "SOURCE-OUTSIDE-SCOPE", source, "incomplete")
                        elif not target.is_file():
                            add(path, 1, "MISSING-SOURCE", source)
        for line, heading in duplicates:
            add(path, line, "DUP-HEADING", heading, "warning")
        if re.search(r"conflicted copy|충돌.*사본|사본.*충돌", path.name, re.I):
            add(path, 1, "CONFLICT-COPY", "compare both versions manually", "warning")

    if not pages:
        add(wiki, 1, "NO-PAGES", "no readable Markdown pages", "incomplete")
    for path, (_, tokens, _) in pages.items():
        for token in tokens:
            line = (token.map[0] + 1) if token.map else 1
            if token.type in ("html_inline", "html_block"):
                add(path, line, "HTML-UNCHECKED", "HTML links/anchors require manual review", "incomplete")
            for child in token.children or []:
                if child.type == "html_inline":
                    add(path, line, "HTML-UNCHECKED", "HTML links/anchors require manual review", "incomplete")
                if child.type == "text" and re.search(r"\[\[.*?\]\]", child.content):
                    add(path, line, "WIKILINK-UNCHECKED", child.content, "incomplete")
                if child.type not in ("link_open", "image"):
                    continue
                dest = child.attrGet("href" if child.type == "link_open" else "src") or ""
                try:
                    url = urlsplit(dest)
                except ValueError:
                    add(path, line, "INVALID-LINK", dest)
                    continue
                if url.scheme or url.netloc:
                    continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                if not target.is_relative_to(boundary):
                    add(path, line, "LINK-OUTSIDE-SCOPE", dest, "incomplete")
                    continue
                if not target.exists():
                    add(path, line, "BROKEN-LINK", dest)
                    continue
                if target in pages:
                    if target != path:
                        graph[path].add(target)
                    if url.fragment and unquote(url.fragment) not in pages[target][2]:
                        add(path, line, "BROKEN-ANCHOR", dest)
                elif url.fragment:
                    add(path, line, "ANCHOR-UNCHECKED", dest, "incomplete")

    inbound = set().union(*graph.values()) if graph else set()
    for path in pages:
        if path.relative_to(wiki).as_posix() not in hubs and path not in inbound:
            add(path, 1, "ORPHAN", "no inbound link from another scanned page", "warning")
    return dict(pages=len(pages), findings=findings, semantic_review="not performed")


def exit_code(report):
    levels = {item["severity"] for item in report["findings"]}
    return 2 if "incomplete" in levels else 1 if "error" in levels else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wiki")
    parser.add_argument("--source-root")
    parser.add_argument("--hub", action="append", help="relative hub filename; replaces defaults")
    parser.add_argument("--types", help="comma-separated allowed types; replaces defaults")
    parser.add_argument("--exclude", action="append", help="excluded path component; replaces defaults")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = inspect(args.wiki, args.source_root, args.hub,
                         args.types.split(",") if args.types else None, args.exclude)
    except OSError as exc:
        print(f"Incomplete: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Scanned {report['pages']} pages; semantic review NOT performed.")
        for item in report["findings"]:
            print(f"{item['file']}:{item['line']} [{item['severity']}:{item['code']}] {item['detail']}")
        print(f"Findings: {len(report['findings'])}; exit={exit_code(report)}")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
