// PreToolUse hook: denies a write to the project's Claude config (.claude/, CLAUDE.md, AGENTS.md)
// until this session has invoked the skills that govern that file (.claude/rules/claude-config.md "Skills per file").
// Reads the session transcript to see which skills were invoked.
// Fails open on unreadable input, and says so (systemMessage + stderr) instead of staying silent.

import * as fs from 'node:fs';

const BASE_SKILLS = ['claude-core-concepts', 'claude-best-practices'];
const MEMORY_SKILLS = ['claude-memory'];
const SKILL_AUTHORING_SKILLS = ['building-skills'];
const SETTINGS_SKILLS = ['update-config'];
const PROSE_SKILLS = ['high-quality-tokens'];

const FILE_TOOLS = ['Edit', 'Write', 'MultiEdit', 'NotebookEdit'];
const SHELL_TOOLS = ['Bash', 'PowerShell'];
const INSTRUCTION_FILE_NAMES = ['claude.md', 'claude.local.md', 'agents.md'];
// A redirect `>` not preceded by a digit (2>), & (&>), - (->) or = (=>), so arrows in commit messages don't count.
const SHELL_WRITE_PATTERN = /(^|[^0-9&=-])>>?(?!\s*\/dev\/null)|\btee\b|\bsed\s+-i|\b(mv|cp|rm|mkdir|touch)\s|Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Move-Item|Copy-Item/;
const SHELL_TARGET_PATTERN = /\.claude[\\/]|CLAUDE(\.local)?\.md|AGENTS\.md/;

function normalizePath(path) {
    return path.replace(/\\/g, '/').toLowerCase();
}

function isClaudeConfigPath(filePath, projectDir) {
    const path = normalizePath(filePath);
    const fileName = path.substring(path.lastIndexOf('/') + 1);
    if (INSTRUCTION_FILE_NAMES.includes(fileName)) {
        return true;
    }
    return path.startsWith(normalizePath(projectDir) + '/.claude/');
}

function requiredSkillsForPath(filePath) {
    const path = normalizePath(filePath);
    const fileName = path.substring(path.lastIndexOf('/') + 1);
    const required = [...BASE_SKILLS];

    if (INSTRUCTION_FILE_NAMES.includes(fileName) || path.includes('/.claude/rules/')) {
        required.push(...MEMORY_SKILLS);
    }
    if (path.includes('/.claude/skills/')) {
        required.push(...SKILL_AUTHORING_SKILLS);
    }
    if (fileName.startsWith('settings') && fileName.endsWith('.json') || path.includes('/.claude/hooks/')) {
        required.push(...SETTINGS_SKILLS);
    }
    if (fileName.endsWith('.md')) {
        required.push(...PROSE_SKILLS);
    }
    return required;
}

function wasSkillInvoked(transcript, skillName) {
    if (transcript.includes('"skill":"' + skillName + '"')) {
        return true;
    }
    return transcript.includes('<command-name>/' + skillName + '</command-name>');
}

function failOpen(what) {
    // The hook cannot tell whether skills were invoked, so the write is allowed.
    // Say so: a silent fail-open means enforcement stops without anyone noticing.
    const message = 'require-claude-skills hook failed open (' + what + '): the Claude-config skill requirement was NOT checked.';
    process.stderr.write(message + '\n');
    process.stdout.write(JSON.stringify({ systemMessage: message }));
}

function deny(target, missingSkills) {
    const reason = 'Writing ' + target + ' requires these skills first (.claude/rules/claude-config.md "Skills per file"). '
        + 'Invoke each with the Skill tool, follow them, then retry: ' + missingSkills.join(', ');
    const output = {
        hookSpecificOutput: {
            hookEventName: 'PreToolUse',
            permissionDecision: 'deny',
            permissionDecisionReason: reason,
        },
    };
    process.stdout.write(JSON.stringify(output));
}

function main() {
    let input = null;
    try {
        input = JSON.parse(fs.readFileSync(0, 'utf8'));
    } catch {
        failOpen('hook input could not be parsed');
        return;
    }

    const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || '';
    const toolInput = input.tool_input || {};
    let target = null;
    let required = null;

    if (FILE_TOOLS.includes(input.tool_name)) {
        const filePath = toolInput.file_path || toolInput.notebook_path || '';
        if (!isClaudeConfigPath(filePath, projectDir)) {
            return;
        }
        target = filePath;
        required = requiredSkillsForPath(filePath);
    } else if (SHELL_TOOLS.includes(input.tool_name)) {
        const command = toolInput.command || '';
        if (!SHELL_TARGET_PATTERN.test(command) || !SHELL_WRITE_PATTERN.test(command)) {
            return;
        }
        target = 'Claude config via ' + input.tool_name;
        required = [...BASE_SKILLS];
    } else {
        return;
    }

    let transcript = '';
    try {
        transcript = fs.readFileSync(input.transcript_path, 'utf8');
    } catch {
        failOpen('transcript could not be read');
        return;
    }

    const missingSkills = [];
    for (const skillName of required) {
        if (!wasSkillInvoked(transcript, skillName)) {
            missingSkills.push(skillName);
        }
    }
    if (missingSkills.length === 0) {
        return;
    }
    deny(target, missingSkills);
}

main();
