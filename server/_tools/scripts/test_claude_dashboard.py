#!/usr/bin/env python3
"""Tests for claude_dashboard.py: each case is one measurement rule and the answer it must give.

Usage: python test_claude_dashboard.py
Exit code: 0 if every case passes, 1 otherwise. Standard library only.
"""
import importlib.util
import pathlib
import re
import sys

testConfig = {
    "dashboardPath": pathlib.Path(__file__).resolve().parent / "claude_dashboard.py",
}


def load_dashboard():
    specification = importlib.util.spec_from_file_location("claude_dashboard", testConfig["dashboardPath"])
    dashboard = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(dashboard)
    return dashboard


def glob_cases():
    # (glob, path, should match): the shapes used in .claude/rules/*.md paths:
    return [
        ("**/*.{cs,ts,js,vue,rs}", "Program.cs", True),
        ("**/*.{cs,ts,js,vue,rs}", "src/features/a/b.vue", True),
        ("**/*.{cs,ts,js,vue,rs}", "src/features/a/b.css", False),
        ("src/**/*.cs", "src/program.cs", True),
        ("src/**/*.cs", "tests/program.cs", False),
        ("src/features/**/infrastructure/**", "src/features/a/b/infrastructure/postgress/Db.cs", True),
        ("src/features/**/infrastructure/**", "src/features/a/b/infrastructure-old/Db.cs", False),
        ("src/features/**/domain/**/*.cs", "src/features/a/b/domain/Loan.cs", True),
        ("**/*Tests.cs", "src/LoanTests.cs", True),
        ("**/*Tests.cs", "src/LoanTests.cs.bak", False),
        ("**/*openapi*.{json,yaml,yml}", "docs/openapi.v1.yaml", True),
        ("*.md", "docs/readme.md", False),
    ]


def load_cases():
    # (component, .claude-relative path, frontmatter, expected load)
    return [
        ("memory", "CLAUDE.md", "", "always"),
        ("rule", "rules/development.md", "", "always"),
        ("rule", "rules/tests.md", "paths:\n  - \"**/*Tests.cs\"", "pathScoped"),
        ("skill", "skills/logging/SKILL.md", "name: logging", "onInvoke"),
        ("skill", "skills/codemath/units-as-types.md", "", "onDemand"),
        ("skill", "skills/building-skills/scripts/validate_skill.py", "", "executed"),
        ("hook", "hooks/require-claude-skills.mjs", "", "executed"),
        ("settings", "settings.json", "", "harness"),
    ]


def frontmatter_cases():
    folded = "name: debug-exception\ndescription: >-\n  Traces a backend exception\n  to its source.\nargument-hint: x"
    quoted = "paths:\n  - \"src/**/*.cs\"\n  - 'src/_config/**'\nother: 1"
    return [
        ("folded description is joined", folded, "description", "Traces a backend exception to its source."),
        ("plain name is read", folded, "name", "debug-exception"),
        ("missing field is empty", folded, "when_to_use", ""),
        ("quoted list items are unquoted", quoted, "paths", ["src/**/*.cs", "src/_config/**"]),
    ]


def main():
    dashboard = load_dashboard()
    failed_count = 0

    for glob, path, expected in glob_cases():
        actual = re.match(dashboard.glob_to_regex(glob), path) is not None
        name = "glob " + glob + (" matches " if expected else " skips ") + path
        if actual != expected:
            failed_count += 1
            print("FAIL  " + name + "  (regex " + dashboard.glob_to_regex(glob) + ")")
        else:
            print("PASS  " + name)

    for component, relative_path, frontmatter, expected in load_cases():
        actual = dashboard.classify_load(component, relative_path, frontmatter)
        name = relative_path + " loads " + expected
        if actual != expected:
            failed_count += 1
            print("FAIL  " + name + "  (got " + actual + ")")
        else:
            print("PASS  " + name)

    for name, frontmatter, key, expected in frontmatter_cases():
        if isinstance(expected, list):
            actual = dashboard.read_frontmatter_list(frontmatter, key)
        else:
            actual = dashboard.read_frontmatter_field(frontmatter, key)
        if actual != expected:
            failed_count += 1
            print("FAIL  " + name + "  (got " + repr(actual) + ")")
        else:
            print("PASS  " + name)

    print(str(failed_count) + " failed")
    if failed_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
