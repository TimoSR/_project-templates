#!/usr/bin/env python3
"""Lint a Claude Code skill directory against the skill-authoring rules.

Usage: python validate_skill.py <skill-dir> [<skill-dir> ...]
Exit code: 0 if no ERRORs, 1 otherwise. Standard library only.
"""
import re
import sys
from pathlib import Path

# Limits from the Agent Skills spec and Claude Code docs.
NAME_MAX = 64
DESC_SPEC_MAX = 1024          # API / Agent Skills spec limit
DESC_CLAUDE_CODE_MAX = 1536   # Claude Code cap for description + when_to_use
BODY_WARN_LINES = 300         # past this, consider moving detail to supporting files
BODY_MAX_LINES = 500          # documented ceiling for SKILL.md
TOC_THRESHOLD_LINES = 100     # longer reference files need a contents list

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
XML_RE = re.compile(r"<[A-Za-z/][^>]*>")


class Report:
    def __init__(self, skill_dir):
        self.skill_dir = skill_dir
        self.errors, self.warnings = [], []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def print(self):
        print(f"== {self.skill_dir}")
        for m in self.errors:
            print(f"  ERROR: {m}")
        for m in self.warnings:
            print(f"  WARN:  {m}")
        if not self.errors and not self.warnings:
            print("  OK")


def parse_frontmatter(text):
    """Return (fields, body, error). Handles `key: value`, quoted values,
    folded/literal block scalars and indented YAML lists well enough to lint."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "first line must be '---' (frontmatter missing)"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, text, "frontmatter is not closed with '---'"

    fields, key = {}, None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if m and not raw[0].isspace():
            key, value = m.group(1), m.group(2).strip()
            if value in (">", "|", ">-", "|-", ">+", "|+"):
                value = ""
            fields[key] = value.strip("'\"") if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"" else value
        elif key is not None:
            fields[key] = (fields[key] + " " + raw.strip().lstrip("- ")).strip()
    body = "\n".join(lines[end + 1:])
    return fields, body, None


def strip_code(text):
    text = FENCE_RE.sub("", text)
    return re.sub(r"`[^`\n]*`", "", text)


def local_links(text):
    links = []
    for target in LINK_RE.findall(strip_code(text)):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            continue  # URL or same-file anchor
        links.append(target)
    return links


def check_links(report, source, text, skill_dir):
    """Validate relative links in `source`; return the set of resolved local files."""
    resolved = set()
    for target in local_links(text):
        if "\\" in target:
            report.error(f"{source.name}: backslash in link '{target}' (use forward slashes)")
            continue
        path = (source.parent / target.split("#", 1)[0]).resolve()
        if not path.exists():
            report.error(f"{source.name}: broken link '{target}'")
        elif skill_dir.resolve() in path.parents or path == skill_dir.resolve():
            resolved.add(path)
    return resolved


def lint(skill_dir):
    report = Report(skill_dir)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        report.error("SKILL.md not found")
        return report

    text = skill_md.read_text(encoding="utf-8")
    fields, body, fm_error = parse_frontmatter(text)
    if fm_error:
        report.error(fm_error)
        fields = {}

    # name
    name = fields.get("name") or skill_dir.name
    if not NAME_RE.match(name):
        report.error(f"name '{name}' must be lowercase letters, digits and single hyphens")
    if len(name) > NAME_MAX:
        report.error(f"name is {len(name)} chars (max {NAME_MAX})")
    if "anthropic" in name.lower() or "claude" in name.lower():
        report.warn(f"name '{name}' contains a reserved word (anthropic/claude): fine in Claude Code, rejected on claude.ai/API upload")
    if fields.get("name") and fields["name"] != skill_dir.name:
        report.warn(f"name '{fields['name']}' differs from directory '{skill_dir.name}'")

    # description
    desc = fields.get("description", "")
    manual_only = fields.get("disable-model-invocation", "").lower() in ("true", "yes", "on", "1")
    if not desc:
        (report.warn if manual_only else report.error)("description is missing")
    else:
        combined = len(desc) + len(fields.get("when_to_use", ""))
        if combined > DESC_CLAUDE_CODE_MAX:
            report.error(f"description + when_to_use is {combined} chars (Claude Code cap {DESC_CLAUDE_CODE_MAX})")
        elif len(desc) > DESC_SPEC_MAX:
            report.warn(f"description is {len(desc)} chars (spec max {DESC_SPEC_MAX})")
        if XML_RE.search(desc):
            report.error("description contains XML/HTML tags")
        if re.match(r"^(I|I'm|I'll|You|Your)\b", desc) or re.search(r"\b(I can|you can)\b", desc, re.I):
            report.warn("description should be third person (not 'I'/'you')")
        if not manual_only and not re.search(r"\b(use (it |this )?(when|whenever|for|if)|when the user)\b", desc, re.I):
            report.warn("description has no 'Use when ...' trigger clause")

    # body size
    body_lines = len(body.splitlines())
    if body_lines > BODY_MAX_LINES:
        report.error(f"SKILL.md body is {body_lines} lines (max {BODY_MAX_LINES}); move detail to supporting files")
    elif body_lines > BODY_WARN_LINES:
        report.warn(f"SKILL.md body is {body_lines} lines; consider moving detail to supporting files")
    if not body.strip():
        report.error("SKILL.md body is empty")

    # links, nesting and supporting files
    direct = check_links(report, skill_md, body, skill_dir)
    for f in sorted(skill_dir.rglob("*")):
        if not f.is_file() or f == skill_md or "__pycache__" in f.parts:
            continue
        rel = f.relative_to(skill_dir).as_posix()
        if f.resolve() not in direct and rel not in text and f.name not in text:
            report.warn(f"{rel} is never referenced from SKILL.md")
        if f.suffix.lower() == ".md":
            content = f.read_text(encoding="utf-8")
            nested = check_links(report, f, content, skill_dir) - direct - {skill_md.resolve()}
            for n in sorted(nested):
                report.warn(f"{rel} links to {n.relative_to(skill_dir.resolve()).as_posix()}, "
                            "which SKILL.md does not link directly (keep references one level deep)")
            if len(content.splitlines()) > TOC_THRESHOLD_LINES and not re.search(r"^#+\s*(table of )?contents\b", content, re.I | re.M):
                report.warn(f"{rel} is over {TOC_THRESHOLD_LINES} lines and has no 'Contents' section")
    return report


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip())
        return 2
    failed = False
    for arg in argv[1:]:
        path = Path(arg).resolve()
        if path.is_file() and path.name == "SKILL.md":
            path = path.parent
        report = lint(path)
        report.print()
        failed |= bool(report.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
