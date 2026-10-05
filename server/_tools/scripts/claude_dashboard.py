#!/usr/bin/env python3
"""Measure every part of the project's .claude/ setup and write one self-contained HTML dashboard.

Usage: python claude_dashboard.py [--root <project-dir>] [--out <file.html>] [--context-window <tokens>] [--no-open]
Or click: VS Code Run and Debug → "Claude dashboard" → ▶ (F5), or double-click claude-dashboard.cmd in Explorer.
Standard library only. Opens the written file in the default browser; it needs no network.

Token counts are estimates: characters / 4, the common rule of thumb for English text.
Code, tables and non-English text usually tokenize denser, so treat the numbers as relative sizes.
"""
import argparse
import datetime
import importlib.util
import json
import math
import pathlib
import re
import subprocess
import sys
import webbrowser

dashboardConfig = {
    "charactersPerToken": 4,                 # estimate: characters / 4 ≈ tokens
    "contextWindowTokens": 200000,           # tokens; the budget bar's 100 %
    "skillDescriptionLimit": 1024,           # characters, Agent Skills spec
    "skillBodyLimitLines": 500,              # lines, documented SKILL.md ceiling
    "ignoredRepositoryParts": [".git", "node_modules", "bin", "obj", "__pycache__"],
    "placeholderFileNames": [".gitkeep"],    # never read by Claude, so never a rule match
    "pathReferenceExtensions": [".md", ".py", ".mjs", ".js", ".json", ".html"],
    "instructionFileNames": ["CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"],
    "validatorPath": ".claude/skills/building-skills/scripts/validate_skill.py",
    "defaultOutputName": "claude_dashboard.html",
}

loadConfig = {
    "always": "Always: loaded at session start",
    "listing": "Always: skill listing (name + description)",
    "pathScoped": "Path-scoped: loads when a matching file is read",
    "onInvoke": "On invoke: skill body",
    "onDemand": "On demand: Claude reads it when the skill points there",
    "executed": "Executed: only its output reaches context",
    "harness": "Harness: read by Claude Code, not by the model",
}

MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CODE_FENCE_PATTERN = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
IMPORT_PATTERN = re.compile(r"(?:^|\s)@([\w./~-]+\.\w+)", re.M)
SKILL_TABLE_HEADING = "## Skills by where you work"


def estimate_tokens(text):
    if len(text) == 0:
        return 0
    return math.ceil(len(text) / dashboardConfig["charactersPerToken"])


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def split_frontmatter(text):
    """Return (frontmatter_text, body_text). No frontmatter → ("", text)."""
    lines = text.splitlines()
    if len(lines) == 0 or lines[0].strip() != "---":
        return "", text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1:])
    return "", text


def read_frontmatter_field(frontmatter, key):
    """Read a scalar or folded (>-, |) field; enough for name, description, when_to_use."""
    lines = frontmatter.splitlines()
    value = None
    for line in lines:
        if value is None:
            match = re.match(r"^" + re.escape(key) + r":\s*(.*)$", line)
            if match:
                value = match.group(1).strip()
                if value in (">", "|", ">-", "|-", ">+", "|+"):
                    value = ""
            continue
        if len(line) > 0 and not line[0].isspace():
            break
        value = (value + " " + line.strip()).strip()
    if value is None:
        return ""
    if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value


def read_frontmatter_list(frontmatter, key):
    """Read a YAML block list (`paths:` followed by `- "glob"` lines)."""
    items = []
    inside = False
    for line in frontmatter.splitlines():
        if not inside:
            if re.match(r"^" + re.escape(key) + r":\s*$", line):
                inside = True
            continue
        stripped = line.strip()
        if not stripped.startswith("-"):
            break
        item = stripped[1:].strip()
        if len(item) > 1 and item[0] == item[-1] and item[0] in "'\"":
            item = item[1:-1]
        items.append(item)
    return items


def glob_to_regex(glob):
    """Convert a rules `paths:` glob to an anchored regex: ** spans folders, * stays in one, {a,b} is a choice."""
    pattern = ""
    index = 0
    brace_depth = 0
    while index < len(glob):
        character = glob[index]
        if glob.startswith("**/", index):
            pattern += "(?:.*/)?"
            index += 3
            continue
        if glob.startswith("/**", index) and index + 3 == len(glob):
            pattern += "(?:/.*)?"
            index += 3
            continue
        if glob.startswith("**", index):
            pattern += ".*"
            index += 2
            continue
        if character == "*":
            pattern += "[^/]*"
        elif character == "?":
            pattern += "[^/]"
        elif character == "{":
            pattern += "(?:"
            brace_depth += 1
        elif character == "}" and brace_depth > 0:
            pattern += ")"
            brace_depth -= 1
        elif character == "," and brace_depth > 0:
            pattern += "|"
        else:
            pattern += re.escape(character)
        index += 1
    return "^" + pattern + "$"


def code_share(text):
    """Fraction of characters inside fenced code blocks: how much of the file is example."""
    if len(text) == 0:
        return 0.0
    fenced = 0
    for match in CODE_FENCE_PATTERN.finditer(text):
        fenced += len(match.group(0))
    return fenced / len(text)


def classify_component(relative_path):
    """Map a .claude-relative path to (component, owner): owner is the skill or rule name."""
    parts = relative_path.split("/")
    if len(parts) >= 3 and parts[0] == "skills":
        return "skill", parts[1]
    if len(parts) >= 2 and parts[0] == "rules":
        return "rule", pathlib.PurePosixPath(parts[-1]).stem
    if len(parts) >= 2 and parts[0] == "hooks":
        return "hook", parts[-1]
    if len(parts) >= 2 and parts[0] == "agents":
        return "agent", pathlib.PurePosixPath(parts[-1]).stem
    if len(parts) >= 2 and parts[0] == "commands":
        return "command", pathlib.PurePosixPath(parts[-1]).stem
    if parts[-1] in dashboardConfig["instructionFileNames"]:
        return "memory", parts[-1]
    if parts[-1].startswith("settings") and parts[-1].endswith(".json"):
        return "settings", parts[-1]
    return "other", parts[-1]


def classify_load(component, relative_path, frontmatter):
    """When does this file reach the model's context?"""
    file_name = relative_path.split("/")[-1]
    is_markdown = file_name.endswith(".md")
    if component == "memory":
        return "always"
    if component == "rule":
        if len(read_frontmatter_list(frontmatter, "paths")) > 0:
            return "pathScoped"
        return "always"
    if component == "skill":
        if file_name == "SKILL.md":
            return "onInvoke"
        if is_markdown or file_name.endswith(".html"):
            return "onDemand"
        return "executed"
    if component == "hook":
        return "executed"
    if component == "agent" or component == "command":
        return "onInvoke"
    return "harness"


def list_repository_files(root):
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        skip = False
        for part in relative.split("/"):
            if part in dashboardConfig["ignoredRepositoryParts"]:
                skip = True
                break
        if skip:
            continue
        files.append(relative)
    files.sort()
    return files


def read_git_history(root):
    """Return ({path: {"lastCommit", "commits"}}, {path: status}) for paths relative to root."""
    history = {}
    statuses = {}
    try:
        log = subprocess.run(
            ["git", "-C", str(root), "log", "--relative", "--name-only", "--format=@%cs", "--", "."],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all", "--relative", "--", "."],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
    except OSError:
        return history, statuses
    current_date = None
    for line in log.stdout.splitlines():
        if line.startswith("@"):
            current_date = line[1:]
            continue
        if len(line.strip()) == 0:
            continue
        if line not in history:
            history[line] = {"lastCommit": current_date, "commits": 0}
        history[line]["commits"] += 1
    for line in status.stdout.splitlines():
        if len(line) < 4:
            continue
        code = line[:2].strip()
        path = line[3:].strip().strip('"')
        statuses[path] = "untracked" if code == "??" else "modified"
    return history, statuses


def load_validator(root):
    validator_path = root / dashboardConfig["validatorPath"]
    if not validator_path.is_file():
        return None
    specification = importlib.util.spec_from_file_location("validate_skill", validator_path)
    validator = importlib.util.module_from_spec(specification)
    try:
        specification.loader.exec_module(validator)
    except Exception:
        return None
    return validator


def resolve_reference(reference, source_path, root):
    """Try the places a reference can be relative to: its file, .claude/, the project, the project's parent."""
    target = reference.split("#", 1)[0]
    if len(target) == 0:
        return True
    candidates = [source_path.parent / target, root / ".claude" / target, root / target, root.parent / target]
    for candidate in candidates:
        if candidate.exists():
            return True
    return False


def find_broken_references(text, source_path, root):
    """Markdown links and backtick paths (`rules/security.md`) that point at a missing file."""
    broken = []
    prose = CODE_FENCE_PATTERN.sub("", text)
    for target in MARKDOWN_LINK_PATTERN.findall(INLINE_CODE_PATTERN.sub("", prose)):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            continue
        if not resolve_reference(target, source_path, root):
            broken.append({"reference": target, "kind": "link"})
    for candidate in INLINE_CODE_PATTERN.findall(prose):
        candidate = candidate.strip()
        if " " in candidate or "/" not in candidate or "*" in candidate or "<" in candidate:
            continue
        if candidate[0] in "~/$":
            continue  # home, absolute and ${VAR} paths live outside the project by design
        has_extension = False
        for extension in dashboardConfig["pathReferenceExtensions"]:
            if candidate.endswith(extension):
                has_extension = True
                break
        if not has_extension:
            continue
        if not resolve_reference(candidate, source_path, root):
            broken.append({"reference": candidate, "kind": "path"})
    return broken


def parse_skill_table(claude_text):
    """Rows of CLAUDE.md "Skills by where you work": [{"where", "fragments", "skills"}]."""
    rows = []
    start = claude_text.find(SKILL_TABLE_HEADING)
    if start < 0:
        return rows
    for line in claude_text[start:].splitlines()[1:]:
        if line.startswith("## "):
            break
        if not line.startswith("|") or "---" in line:
            continue
        cells = line.strip().strip("|").split("|")
        if len(cells) < 2 or cells[1].strip() == "Skill":
            continue
        rows.append({
            "where": cells[0].strip(),
            "fragments": INLINE_CODE_PATTERN.findall(cells[0]),
            "skills": INLINE_CODE_PATTERN.findall(cells[1]),
        })
    return rows


def measure(root):
    claude_directory = root / ".claude"
    repository_files = list_repository_files(root)
    history, statuses = read_git_history(root)
    validator = load_validator(root)

    readable_files = []
    for relative in repository_files:
        file_name = relative.split("/")[-1]
        if file_name in dashboardConfig["placeholderFileNames"]:
            continue
        if relative.startswith(".claude/"):
            continue
        readable_files.append(relative)

    files = []
    issues = []
    for path in sorted(claude_directory.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative_to_claude = path.relative_to(claude_directory).as_posix()
        relative = ".claude/" + relative_to_claude
        text = read_text(path)
        if text is None:
            text = ""
        frontmatter, body = split_frontmatter(text)
        component, owner = classify_component(relative_to_claude)
        load = classify_load(component, relative_to_claude, frontmatter)
        git = history.get(relative, {"lastCommit": None, "commits": 0})
        record = {
            "path": relative,
            "component": component,
            "owner": owner,
            "load": load,
            "bytes": path.stat().st_size,
            "lines": len(text.splitlines()),
            "words": len(text.split()),
            "tokens": estimate_tokens(text),
            "bodyTokens": estimate_tokens(body),
            "codeShare": round(code_share(text), 3),
            "headings": len(re.findall(r"^#{1,6} ", text, re.M)),
            "lastCommit": git["lastCommit"],
            "commits": git["commits"],
            "status": statuses.get(relative, "clean"),
        }
        files.append(record)
        if path.suffix == ".md":
            seen_references = set()
            for broken in find_broken_references(text, path, root):
                if broken["reference"] in seen_references:
                    continue
                seen_references.add(broken["reference"])
                if broken["kind"] == "link":
                    issues.append({"severity": "error", "where": relative, "message": "broken link `" + broken["reference"] + "`"})
                    continue
                issues.append({
                    "severity": "info",
                    "where": relative,
                    "message": "backtick path `" + broken["reference"] + "` does not exist here (an example, or written for another repo?)",
                })

    rules = []
    for record in files:
        if record["component"] != "rule":
            continue
        frontmatter, body = split_frontmatter(read_text(root / record["path"]) or "")
        globs = []
        total_matches = 0
        for glob in read_frontmatter_list(frontmatter, "paths"):
            regex = glob_to_regex(glob)
            compiled = re.compile(regex)
            matches = []
            for relative in readable_files:
                if compiled.match(relative):
                    matches.append(relative)
            total_matches += len(matches)
            globs.append({"glob": glob, "regex": regex, "matches": len(matches), "examples": matches[:5]})
        rules.append({
            "name": record["owner"],
            "path": record["path"],
            "load": record["load"],
            "tokens": record["tokens"],
            "globs": globs,
            "matches": total_matches,
        })
        if record["load"] == "pathScoped" and total_matches == 0:
            issues.append({
                "severity": "info",
                "where": record["path"],
                "message": "no file in the project matches its paths yet, so it never loads",
            })

    claude_text = read_text(claude_directory / "CLAUDE.md") or ""
    skill_table = parse_skill_table(claude_text)
    table_skills = set()
    for row in skill_table:
        for skill_name in row["skills"]:
            table_skills.add(skill_name)

    skills = []
    for skill_directory in sorted((claude_directory / "skills").glob("*/")):
        skill_file = skill_directory / "SKILL.md"
        if not skill_file.is_file():
            continue
        name_key = skill_directory.name
        text = read_text(skill_file) or ""
        frontmatter, body = split_frontmatter(text)
        name = read_frontmatter_field(frontmatter, "name") or name_key
        description = read_frontmatter_field(frontmatter, "description")
        when_to_use = read_frontmatter_field(frontmatter, "when_to_use")
        listing = "- " + name + ": " + description + (" " + when_to_use if when_to_use else "")
        supporting_tokens = 0
        script_count = 0
        file_count = 0
        last_commit = None
        for record in files:
            if record["component"] != "skill" or record["owner"] != name_key:
                continue
            file_count += 1
            if record["lastCommit"] and (last_commit is None or record["lastCommit"] > last_commit):
                last_commit = record["lastCommit"]
            if record["load"] == "onDemand":
                supporting_tokens += record["tokens"]
            if record["load"] == "executed":
                script_count += 1
        lint_errors = []
        lint_warnings = []
        if validator is not None:
            report = validator.lint(skill_directory)
            lint_errors = report.errors
            lint_warnings = report.warnings
        skills.append({
            "name": name,
            "directory": ".claude/skills/" + name_key,
            "descriptionCharacters": len(description) + len(when_to_use),
            "listingTokens": estimate_tokens(listing),
            "bodyTokens": estimate_tokens(body),
            "bodyLines": len(body.splitlines()),
            "supportingTokens": supporting_tokens,
            "files": file_count,
            "scripts": script_count,
            "inSkillTable": name in table_skills,
            "manualOnly": read_frontmatter_field(frontmatter, "disable-model-invocation").lower() == "true",
            "lastCommit": last_commit,
            "lintErrors": lint_errors,
            "lintWarnings": lint_warnings,
        })
        for message in lint_errors:
            issues.append({"severity": "error", "where": ".claude/skills/" + name_key, "message": message})
        for message in lint_warnings:
            issues.append({"severity": "warning", "where": ".claude/skills/" + name_key, "message": message})
        if name not in table_skills:
            issues.append({
                "severity": "info",
                "where": ".claude/skills/" + name_key,
                "message": "not named in CLAUDE.md \"Skills by where you work\"",
            })

    local_skill_names = set()
    for skill in skills:
        local_skill_names.add(skill["name"])
    for skill_name in sorted(table_skills):
        if skill_name in local_skill_names:
            continue
        issues.append({
            "severity": "warning",
            "where": ".claude/CLAUDE.md",
            "message": "skill table names `" + skill_name + "`, which is not in .claude/skills/ (built-in or missing)",
        })

    imports = []
    for match in IMPORT_PATTERN.findall(CODE_FENCE_PATTERN.sub("", claude_text)):
        imports.append(match)

    hooks = []
    permissions = {"allow": [], "deny": [], "ask": []}
    settings_text = read_text(claude_directory / "settings.json")
    if settings_text:
        try:
            settings = json.loads(settings_text)
        except json.JSONDecodeError:
            settings = {}
            issues.append({"severity": "error", "where": ".claude/settings.json", "message": "invalid JSON"})
        for event in settings.get("hooks", {}):
            for group in settings["hooks"][event]:
                for hook in group.get("hooks", []):
                    hooks.append({
                        "event": event,
                        "matcher": group.get("matcher", "*"),
                        "type": hook.get("type", ""),
                        "command": hook.get("command", hook.get("prompt", "")),
                        "timeout": hook.get("timeout"),
                    })
        for key in permissions:
            permissions[key] = settings.get("permissions", {}).get(key, [])

    always_tokens = 0
    listing_tokens = 0
    for record in files:
        if record["load"] == "always":
            always_tokens += record["tokens"]
    for skill in skills:
        listing_tokens += skill["listingTokens"]

    head = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True, check=False).stdout.strip()

    return {
        "project": root.name,
        "root": str(root),
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "head": head,
        "config": {
            "charactersPerToken": dashboardConfig["charactersPerToken"],
            "contextWindowTokens": dashboardConfig["contextWindowTokens"],
            "skillDescriptionLimit": dashboardConfig["skillDescriptionLimit"],
            "skillBodyLimitLines": dashboardConfig["skillBodyLimitLines"],
        },
        "loadLabels": loadConfig,
        "totals": {
            "alwaysTokens": always_tokens,
            "listingTokens": listing_tokens,
            "projectFiles": len(readable_files),
        },
        "files": files,
        "skills": skills,
        "rules": rules,
        "skillTable": skill_table,
        "imports": imports,
        "hooks": hooks,
        "permissions": permissions,
        "issues": issues,
        "readableFiles": readable_files,
    }


def render(data):
    template_path = pathlib.Path(__file__).resolve().parent / "claude_dashboard_template.html"
    template = template_path.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("/*__DATA__*/null", payload)


def main(argv):
    parser = argparse.ArgumentParser(description="Write an HTML dashboard of the project's .claude/ setup.")
    parser.add_argument("--root", default=None, help="project directory (default: the git top level of this script's project)")
    parser.add_argument("--out", default=None, help="output HTML file (default: next to this script)")
    parser.add_argument("--context-window", type=int, default=None, help="tokens, the budget bar's 100 %%")
    parser.add_argument("--no-open", action="store_true", help="write the file without opening it in the browser")
    arguments = parser.parse_args(argv[1:])

    script_directory = pathlib.Path(__file__).resolve().parent
    root = pathlib.Path(arguments.root).resolve() if arguments.root else script_directory.parent.parent
    if not (root / ".claude").is_dir():
        print("no .claude/ directory in " + str(root))
        return 1
    if arguments.context_window:
        dashboardConfig["contextWindowTokens"] = arguments.context_window

    data = measure(root)
    output_path = pathlib.Path(arguments.out).resolve() if arguments.out else script_directory / dashboardConfig["defaultOutputName"]
    output_path.write_text(render(data), encoding="utf-8")

    print("files   " + str(len(data["files"])))
    print("always  ~" + str(data["totals"]["alwaysTokens"] + data["totals"]["listingTokens"]) + " tokens")
    print("issues  " + str(len(data["issues"])))
    print("wrote   " + output_path.as_uri())
    if not arguments.no_open:
        webbrowser.open(output_path.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
