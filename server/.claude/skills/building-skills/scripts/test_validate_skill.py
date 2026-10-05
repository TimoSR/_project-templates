#!/usr/bin/env python3
"""Tests for validate_skill.py: each case is one skill-authoring rule and the finding it must produce.

Usage: python test_validate_skill.py
Exit code: 0 if every case passes, 1 otherwise. Standard library only.
"""
import importlib.util
import io
import pathlib
import shutil
import sys
import tempfile

testConfig = {
    "validatorPath": pathlib.Path(__file__).resolve().parent / "validate_skill.py",
    "skillName": "fixture-skill",
    "description": "Checks fixture skills. Use when testing the validator.",
    "codeLineCount": 200,              # ~3,400 characters of code before the cut
    "headingPastCutCharacters": 500,   # below the code length, so shifted offsets would hide the heading
}


def load_validator():
    specification = importlib.util.spec_from_file_location("validate_skill", testConfig["validatorPath"])
    validator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(validator)
    return validator


def write_skill(root, frontmatter, body, extra_files):
    skill_directory = root / testConfig["skillName"]
    skill_directory.mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text("---\n" + frontmatter + "\n---\n" + body, encoding="utf-8")
    for relative_path in extra_files:
        file_path = skill_directory / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(extra_files[relative_path], encoding="utf-8")
    return skill_directory


def default_frontmatter():
    return "name: " + testConfig["skillName"] + "\ndescription: " + testConfig["description"]


def contains_finding(findings, expected_text):
    for finding in findings:
        if expected_text in finding:
            return True
    return False


def run_case(validator, case):
    root = pathlib.Path(tempfile.mkdtemp())
    skill_directory = write_skill(root, case["frontmatter"], case["body"], case["files"])
    if case.get("bom"):
        skill_path = skill_directory / "SKILL.md"
        skill_path.write_bytes(b"\xef\xbb\xbf" + skill_path.read_bytes())
    report = validator.lint(skill_directory)
    shutil.rmtree(root)

    problems = []
    for expected_text in case.get("errors", []):
        if not contains_finding(report.errors, expected_text):
            problems.append("missing ERROR containing '" + expected_text + "'")
    for expected_text in case.get("warnings", []):
        if not contains_finding(report.warnings, expected_text):
            problems.append("missing WARN containing '" + expected_text + "'")
    if case.get("clean") and (report.errors or report.warnings):
        problems.append("expected no findings, got " + repr(report.errors + report.warnings))
    if case.get("noErrors") and report.errors:
        problems.append("expected no ERROR, got " + repr(report.errors))
    return problems


def run_parent_directory_case(validator):
    root = pathlib.Path(tempfile.mkdtemp())
    write_skill(root, default_frontmatter(), "# Body\n", {})
    second_directory = root / "second-skill"
    second_directory.mkdir()
    (second_directory / "SKILL.md").write_text("---\nname: second-skill\n---\n# Body\n", encoding="utf-8")

    captured_output = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured_output
    exit_code = validator.main(["validate_skill.py", str(root)])
    sys.stdout = original_stdout
    shutil.rmtree(root)

    output = captured_output.getvalue()
    problems = []
    if "SKILL.md not found" in output:
        problems.append("a directory of skills was linted as one skill")
    if "description is missing" not in output:
        problems.append("second-skill was not linted")
    if exit_code != 1:
        problems.append("exit code " + str(exit_code) + ", expected 1 (second-skill has an ERROR)")
    return problems


def build_cases(validator):
    cut_characters = validator.COMPACTION_KEEP_TOKENS * validator.CHARS_PER_TOKEN
    long_body = "## Rules\n\n```csharp\n" + "var padding = 0;\n" * testConfig["codeLineCount"] + "```\n\n"
    line_number = 0
    while len(long_body) < cut_characters + testConfig["headingPastCutCharacters"]:
        long_body += "* Filler rule number " + str(line_number) + " that pads the body past the compaction cut.\n"
        line_number += 1
    long_body += "\n## Late section\n\n* Lost after compaction.\n"

    return [
        {"name": "valid skill has no findings", "frontmatter": default_frontmatter(),
         "body": "# Title\n\n## Rules\n\n* See [rules](#rules).\n", "files": {}, "clean": True},

        # YAML traps, each checked against what Claude Code loads (claude plugin validate + a headless session):
        # malformed YAML loads with empty metadata, ' #' cuts the value, the rest only strict parsers reject.
        {"name": "value ending in ':' breaks YAML",
         "frontmatter": "name: fixture-skill\ndescription: Lints skills. Use when ready:",
         "body": "# Body\n", "files": {}, "errors": ["ends with ':'"]},
        {"name": "' #' in description silently truncates it",
         "frontmatter": "name: fixture-skill\ndescription: Lints C# skills #1. Use when testing.",
         "body": "# Body\n", "files": {}, "errors": ["' #'"]},
        {"name": "unquoted ': ' loads in Claude Code but strict YAML rejects it",
         "frontmatter": "name: fixture-skill\ndescription: Lints skills. Use when: the user asks.",
         "body": "# Body\n", "files": {}, "warnings": ["': '"], "noErrors": True},
        {"name": "plain scalar starting with an indicator",
         "frontmatter": "name: fixture-skill\ndescription: `validate` skills. Use when testing.",
         "body": "# Body\n", "files": {}, "warnings": ["starts with"], "noErrors": True},
        {"name": "tab indentation breaks YAML",
         "frontmatter": "name: fixture-skill\ndescription: >\n\tLints skills. Use when testing.",
         "body": "# Body\n", "files": {}, "errors": ["tab"]},
        {"name": "quoted and folded descriptions are fine",
         "frontmatter": "name: fixture-skill\ndescription: \"Lints C# skills #1: use when testing.\"\nwhen_to_use: >\n  Use when: the validator changes.",
         "body": "# Body\n", "files": {}, "clean": True},

        {"name": "misspelled field is reported (Claude Code ignores it silently)",
         "frontmatter": default_frontmatter() + "\ndisable-model-invocations: true",
         "body": "# Body\n", "files": {}, "warnings": ["unknown frontmatter field 'disable-model-invocations'"]},

        {"name": "broken same-file anchor",
         "frontmatter": default_frontmatter(), "body": "# Body\n\nSee [x](#missing-section).\n",
         "files": {}, "errors": ["broken anchor '#missing-section'"]},
        {"name": "anchors follow GitHub heading slugs",
         "frontmatter": default_frontmatter(),
         "body": "# Body\n\n## 1. Verification\n\n## `paths:` and globs\n\nSee [a](#1-verification), [b](#paths-and-globs), [c](other.md#section-two).\n",
         "files": {"other.md": "# Other\n\n## Section two\n"}, "clean": True},
        {"name": "broken anchor in a linked file",
         "frontmatter": default_frontmatter(), "body": "# Body\n\nSee [x](other.md#nope).\n",
         "files": {"other.md": "# Other\n"}, "errors": ["broken anchor 'other.md#nope'"]},

        {"name": "links inside an indented code fence are not checked",
         "frontmatter": default_frontmatter(),
         "body": "# Body\n\n1. Run:\n   ```markdown\n   [x](missing.md)\n   ```\n", "files": {}, "clean": True},

        {"name": "UTF-8 byte order mark is accepted", "frontmatter": default_frontmatter(),
         "body": "# Body\n", "files": {}, "bom": True, "clean": True},

        {"name": "script path without ${CLAUDE_SKILL_DIR}", "frontmatter": default_frontmatter(),
         "body": "# Body\n\n```bash\npython scripts/check.py\n```\n", "files": {"scripts/check.py": "print('ok')\n"},
         "warnings": ["${CLAUDE_SKILL_DIR}/scripts/check.py"]},
        {"name": "script path with ${CLAUDE_SKILL_DIR}", "frontmatter": default_frontmatter(),
         "body": "# Body\n\n```bash\npython \"${CLAUDE_SKILL_DIR}/scripts/check.py\"\n```\n",
         "files": {"scripts/check.py": "print('ok')\n"}, "clean": True},

        {"name": "time-sensitive statement", "frontmatter": default_frontmatter(),
         "body": "# Body\n\nAs of 2025 the API returns 404.\n", "files": {}, "warnings": ["time-sensitive"]},
        {"name": "year inside code is not time-sensitive", "frontmatter": default_frontmatter(),
         "body": "# Body\n\n```sql\nSELECT 2025;\n```\n", "files": {}, "clean": True},

        {"name": "backslash path in prose", "frontmatter": default_frontmatter(),
         "body": "# Body\n\nRead docs\\guide.md first.\n", "files": {}, "warnings": ["backslash path"]},

        {"name": "body past the compaction cut names the first lost section",
         "frontmatter": default_frontmatter(), "body": long_body, "files": {},
         "warnings": ["Late section"], "noErrors": True},

        {"name": "test files need no reference from SKILL.md", "frontmatter": default_frontmatter(),
         "body": "# Body\n", "files": {"scripts/test_check.py": "print('ok')\n"}, "clean": True},
    ]


def main():
    validator = load_validator()
    failed_count = 0
    for case in build_cases(validator):
        problems = run_case(validator, case)
        if problems:
            failed_count += 1
            print("FAIL  " + case["name"])
            for problem in problems:
                print("        " + problem)
        else:
            print("PASS  " + case["name"])

    problems = run_parent_directory_case(validator)
    if problems:
        failed_count += 1
        print("FAIL  directory of skills lints each skill")
        for problem in problems:
            print("        " + problem)
    else:
        print("PASS  directory of skills lints each skill")

    print(str(failed_count) + " failed")
    if failed_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
