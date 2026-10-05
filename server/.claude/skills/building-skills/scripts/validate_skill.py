#!/usr/bin/env python3
"""Lint a Claude Code skill directory against the skill-authoring rules.

Usage: python validate_skill.py <skill-dir | skills-dir | SKILL.md> [...]
A directory without SKILL.md lints every skill directly inside it (e.g. .claude/skills).
Exit code: 0 if no ERRORs, 1 otherwise. Standard library only.
Tests: python test_validate_skill.py
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
COMPACTION_KEEP_TOKENS = 5000 # after compaction only the top of an invoked skill is re-attached
CHARS_PER_TOKEN = 4           # rough average for English prose and code; the estimate is labelled "~"

# Claude Code fields (building-skills reference §1) plus the Agent Skills spec fields.
KNOWN_FIELDS = {
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "allowed-tools", "disallowed-tools",
    "model", "effort", "context", "agent", "background", "paths", "hooks", "shell",
    "license", "compatibility", "metadata",
}
# Fields whose value is a plain string, so YAML scalar traps apply to them.
STRING_FIELDS = {"name", "description", "when_to_use", "argument-hint", "model", "effort",
                 "context", "agent", "shell", "license", "compatibility"}
YAML_INDICATORS = "`@*&!%|>?,[]{}"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1", re.S | re.M)
HEADING_RE = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", re.M)
HTML_ID_RE = re.compile(r"<[^>]+\b(?:id|name)=\"([^\"]+)\"")
XML_RE = re.compile(r"<[A-Za-z/][^>]*>")
TEST_FILE_RE = re.compile(r"^(test_.+|.+_test\.\w+|.+\.(test|spec)\.\w+)$")
SCRIPT_REF_RE = re.compile(r"(?<![\w/{}.$(-])scripts/[\w.-]+")
TIME_RE = re.compile(
    r"\b(as of|at the time of writing)\b"
    r"|\b(in|since|until|before|after|by)\s+(early |late |mid-)?"
    r"((jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(19|20)\d{2}\b",
    re.I)
BACKSLASH_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s]*|\b[\w.-]+(?:\\[\w.-]+)+\.\w+\b")


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
    """Return (fields, body, error, raw_lines). Handles `key: value`, quoted values,
    folded/literal block scalars and indented YAML lists well enough to lint."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "first line must be '---' (frontmatter missing)", []
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, text, "frontmatter is not closed with '---'", []

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
    return fields, body, None, lines[1:end]


def check_plain_scalar(report, key, value):
    """Flag YAML traps in an unquoted value. Verified against Claude Code: a parse error loads the
    skill with empty metadata; ' #' silently cuts the value; the rest load but strict parsers reject them."""
    if " #" in value:
        kept = value.split(" #", 1)[0]
        report.error(f"{key}: ' #' starts a YAML comment, so the value loads as '{kept}'; quote the value")
    if value.endswith(":"):
        report.error(f"{key}: value ends with ':' (YAML parse error: the skill loads with empty metadata); quote the value")
    elif ": " in value:
        report.warn(f"{key}: unquoted ': ' loads in Claude Code but strict YAML parsers (claude.ai/API upload) reject it; quote the value")
    if value[0] in YAML_INDICATORS:
        report.warn(f"{key}: value starts with '{value[0]}', a YAML indicator; quote the value")


def check_yaml(report, raw_lines):
    key, plain = None, False
    for raw in raw_lines:
        indent = raw[:len(raw) - len(raw.lstrip())]
        if "\t" in indent:
            report.error("frontmatter indents with a tab (YAML parse error: the skill loads with empty metadata)")
            return
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
        if m and not indent:
            key, value = m.group(1), m.group(2).strip()
            if key not in KNOWN_FIELDS:
                report.warn(f"unknown frontmatter field '{key}' (Claude Code ignores it silently; typo?)")
            plain = key in STRING_FIELDS and value != "" and value[0] not in "'\"" \
                and value not in (">", "|", ">-", "|-", ">+", "|+")
            if plain:
                check_plain_scalar(report, key, value)
        elif plain and key is not None:
            check_plain_scalar(report, key, raw.strip())


def strip_code(text):
    text = FENCE_RE.sub("", text)
    return re.sub(r"`[^`\n]*`", "", text)


def heading_slug(heading):
    """GitHub anchor: lowercase, drop punctuation except '-' and '_', spaces become '-'."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors_of(text):
    anchors, seen = set(HTML_ID_RE.findall(text)), {}
    for heading in HEADING_RE.findall(FENCE_RE.sub("", text)):
        slug = heading_slug(heading)
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


def local_links(text):
    links = []
    for target in LINK_RE.findall(strip_code(text)):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            continue  # URL
        links.append(target)
    return links


def check_links(report, source, text, skill_dir):
    """Validate relative links and anchors in `source`; return the set of resolved local files."""
    resolved = set()
    for target in local_links(text):
        if "\\" in target:
            report.error(f"{source.name}: backslash in link '{target}' (use forward slashes)")
            continue
        file_part, _, anchor = target.partition("#")
        path = (source.parent / file_part).resolve() if file_part else source.resolve()
        if not path.exists():
            report.error(f"{source.name}: broken link '{target}'")
            continue
        if anchor and path.suffix.lower() == ".md":
            target_text = text if path == source.resolve() else path.read_text(encoding="utf-8-sig")
            if anchor.lower() not in anchors_of(target_text):
                report.error(f"{source.name}: broken anchor '{target}'")
        if file_part and (skill_dir.resolve() in path.parents or path == skill_dir.resolve()):
            resolved.add(path)
    return resolved


def check_prose(report, source_name, text, skill_dir):
    """Rules that apply to every markdown file of the skill: script paths, time, slashes."""
    for ref in sorted(set(SCRIPT_REF_RE.findall(text))):
        if (skill_dir / ref).is_file():
            report.warn(f"{source_name}: '{ref}' resolves against the project, not the skill; "
                        f"use ${{CLAUDE_SKILL_DIR}}/{ref}")
    prose = strip_code(LINK_RE.sub("", text))
    for m in TIME_RE.finditer(prose):
        report.warn(f"{source_name}: time-sensitive statement '{m.group(0)}' goes stale; state the fact without the date")
    for m in BACKSLASH_PATH_RE.finditer(prose):
        report.warn(f"{source_name}: backslash path '{m.group(0)}' (use forward slashes)")


def check_compaction(report, body):
    """After compaction only the first ~5,000 tokens of the skill return; name what falls past the cut."""
    estimated_tokens = len(body) // CHARS_PER_TOKEN
    if estimated_tokens <= COMPACTION_KEEP_TOKENS:
        return
    cut = COMPACTION_KEEP_TOKENS * CHARS_PER_TOKEN
    code_free = FENCE_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), body)  # same length: offsets stay, '#' in code is ignored
    lost = [m.group(1) for m in HEADING_RE.finditer(code_free) if m.start() >= cut]
    where = f"'{lost[0]}' and later sections" if lost else f"the last ~{(len(body) - cut) // CHARS_PER_TOKEN} tokens"
    report.warn(f"SKILL.md body is ~{estimated_tokens} tokens; after compaction only the first "
                f"~{COMPACTION_KEEP_TOKENS} are re-attached, so {where} drop; keep must-hold rules above that")


def lint(skill_dir):
    report = Report(skill_dir)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        report.error("SKILL.md not found")
        return report

    text = skill_md.read_text(encoding="utf-8-sig")
    fields, body, fm_error, raw_lines = parse_frontmatter(text)
    if fm_error:
        report.error(fm_error)
        fields = {}
    check_yaml(report, raw_lines)

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
    check_compaction(report, body)
    check_prose(report, skill_md.name, body, skill_dir)

    # links, nesting and supporting files
    direct = check_links(report, skill_md, body, skill_dir)
    for f in sorted(skill_dir.rglob("*")):
        if not f.is_file() or f == skill_md or "__pycache__" in f.parts:
            continue
        rel = f.relative_to(skill_dir).as_posix()
        if f.resolve() not in direct and rel not in text and f.name not in text and not TEST_FILE_RE.match(f.name):
            report.warn(f"{rel} is never referenced from SKILL.md")
        if f.suffix.lower() == ".md":
            content = f.read_text(encoding="utf-8-sig")
            nested = check_links(report, f, content, skill_dir) - direct - {skill_md.resolve()}
            for n in sorted(nested):
                report.warn(f"{rel} links to {n.relative_to(skill_dir.resolve()).as_posix()}, "
                            "which SKILL.md does not link directly (keep references one level deep)")
            check_prose(report, rel, content, skill_dir)
            if len(content.splitlines()) > TOC_THRESHOLD_LINES and not re.search(r"^#+\s*(table of )?contents\b", FENCE_RE.sub("", content), re.I | re.M):
                report.warn(f"{rel} is over {TOC_THRESHOLD_LINES} lines and has no 'Contents' section")
    return report


def skill_dirs(path):
    """A skill directory, or each skill directly inside a directory of skills."""
    if path.is_file() and path.name == "SKILL.md":
        return [path.parent]
    if path.is_dir() and not (path / "SKILL.md").exists():
        children = sorted(p for p in path.iterdir() if (p / "SKILL.md").is_file())
        if children:
            return children
    return [path]


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
    if len(argv) < 2:
        print(__doc__.strip())
        return 2
    failed = False
    for arg in argv[1:]:
        for path in skill_dirs(Path(arg).resolve()):
            report = lint(path)
            report.print()
            failed |= bool(report.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
