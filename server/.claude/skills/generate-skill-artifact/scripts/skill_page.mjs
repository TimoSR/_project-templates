#!/usr/bin/env node
// Numbers for a skill page's load profile, and a check that a page follows template.html.
//   node skill_page.mjs stats <skill-dir>    print title, command, invocation, sizes and files
//   node skill_page.mjs check <page.html>    check a page against the standard
// Exit code: 0 when clean, 1 on any ERROR, 2 on bad usage. Node standard library only.
import * as fs from 'node:fs'
import * as path from 'node:path'
import * as url from 'node:url'

const statsConfig = {
  descriptionMaxCharacters: 1024, // Agent Skills spec limit
  skillLinesBudget: 500, // documented ceiling for SKILL.md
  blockScalarMarkers: ['>', '|', '>-', '|-', '>+', '|+'],
  skippedDirectories: ['__pycache__', 'node_modules'],
  scriptExtensions: ['.py', '.mjs', '.js', '.ts', '.sh', '.ps1'], // executed, so only their output costs context
  lowercaseTitleWords: ['a', 'an', 'and', 'as', 'for', 'in', 'of', 'on', 'or', 'the', 'to'],
}

const checkConfig = {
  templatePath: path.join(path.dirname(url.fileURLToPath(import.meta.url)), '..', 'template.html'),
  titleScanCharacters: 8192, // the Artifact tool reads <title> from the first 8KB only
  titleMaxWords: 4,
  titleExplainerPattern: /:| - | — | \| /, // a title is a name, never "Name: explanation"
  forbiddenTagPattern: /<(!doctype|html|head|body)\b/i, // the publish step adds the document skeleton
  fillStylePattern: /^--fill:\s*\d{1,3}%;?$/, // the only inline style allowed: a load-profile bar
  languageClassPattern: /^language-[\w-]+$/, // highlight.js language markers, not in the CSS
  exampleClasses: ['compare', 'code', 'diagram', 'table-wrap', 'mermaid'],
  voidTags: ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'],
  emojiPattern: /[\u{1F000}-\u{1FAFF}]/u,
  statementPreviewCharacters: 70,
  tagPreviewCharacters: 90, // enough to identify a template tag in an error line
}

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8').replace(/\r\n/g, '\n')
}

function countLines(text) {
  if (text === '') {
    return 0
  }
  return text.replace(/\n$/, '').split('\n').length
}

function toFillPercent(value, maximum) {
  return Math.min(100, Math.round((value / maximum) * 100))
}

function readScalar(value) {
  if (statsConfig.blockScalarMarkers.includes(value)) {
    return ''
  }
  const isQuoted = value.length > 1 && value[0] === value[value.length - 1] && (value[0] === '"' || value[0] === "'")
  if (isQuoted) {
    return value.slice(1, -1)
  }
  return value
}

// Top-level `key: value` pairs, quoted values and folded/literal block scalars. Returns null when malformed.
function parseFrontmatter(text) {
  const lines = text.split('\n')
  if (lines[0].trim() !== '---') {
    return null
  }
  const fields = {}
  let key = null
  for (let index = 1; index < lines.length; index++) {
    const line = lines[index]
    if (line.trim() === '---') {
      return fields
    }
    if (line.trim() === '' || line.trimStart().startsWith('#')) {
      continue
    }
    const match = /^([A-Za-z_][\w-]*):\s*(.*)$/.exec(line)
    if (match && !/^\s/.test(line)) {
      key = match[1]
      fields[key] = readScalar(match[2].trim())
      continue
    }
    if (key !== null) {
      fields[key] = (fields[key] + ' ' + line.trim().replace(/^- /, '')).trim()
    }
  }
  return null
}

// "tests-as-documentation" → "Tests as Documentation"
function humanizeSlug(slug) {
  const words = []
  for (const word of slug.split('-')) {
    if (words.length > 0 && statsConfig.lowercaseTitleWords.includes(word)) {
      words.push(word)
      continue
    }
    words.push(word.charAt(0).toUpperCase() + word.slice(1))
  }
  return words.join(' ')
}

// The SKILL.md H1 up to " / " or ": ", humanized when the H1 is just the slug.
function readTitle(skillText, fallbackName) {
  const match = /^# (.+)$/m.exec(skillText)
  const heading = match ? match[1].split(/ \/ |: /)[0].trim() : fallbackName
  if (/^[a-z0-9]+(-[a-z0-9]+)*$/.test(heading)) {
    return humanizeSlug(heading)
  }
  return heading
}

function readInvocation(fields) {
  if (String(fields['disable-model-invocation']).toLowerCase() === 'true') {
    return { label: '/command only', descriptionInContext: false }
  }
  if (String(fields['user-invocable']).toLowerCase() === 'false') {
    return { label: 'Auto only', descriptionInContext: true }
  }
  return { label: 'Auto + /command', descriptionInContext: true }
}

function listSupportingFiles(skillDirectory) {
  const files = []
  const entries = fs.readdirSync(skillDirectory, { recursive: true, withFileTypes: true })
  for (const entry of entries) {
    if (!entry.isFile()) {
      continue
    }
    const fullPath = path.join(entry.parentPath, entry.name)
    const relativePath = path.relative(skillDirectory, fullPath).split(path.sep).join('/')
    if (relativePath === 'SKILL.md') {
      continue
    }
    let isSkipped = false
    for (const directoryName of statsConfig.skippedDirectories) {
      if (relativePath.split('/').includes(directoryName)) {
        isSkipped = true
      }
    }
    if (isSkipped) {
      continue
    }
    files.push({ relativePath: relativePath, lines: countLines(readText(fullPath)) })
  }
  files.sort(function compareFiles(left, right) { return left.relativePath.localeCompare(right.relativePath) })
  return files
}

function printStats(skillDirectory) {
  const skillPath = path.join(skillDirectory, 'SKILL.md')
  if (!fs.existsSync(skillPath)) {
    console.log(`ERROR: no SKILL.md in ${skillDirectory}`)
    return 1
  }
  const skillText = readText(skillPath)
  const fields = parseFrontmatter(skillText)
  if (fields === null) {
    console.log('ERROR: SKILL.md frontmatter is missing or not closed with ---')
    return 1
  }
  const name = fields.name || path.basename(path.resolve(skillDirectory))
  const invocation = readInvocation(fields)
  const descriptionCharacters = (fields.description || '').length
  const skillLines = countLines(skillText)
  const argumentHint = fields['argument-hint'] ? ' ' + fields['argument-hint'] : ''

  console.log(`name         ${name}`)
  console.log(`title        ${readTitle(skillText, name)}`)
  console.log(`command      /${name}${argumentHint}`)
  console.log(`invocation   ${invocation.label} (description ${invocation.descriptionInContext ? 'always in context' : 'not in context'})`)
  console.log(`description  ${descriptionCharacters} / ${statsConfig.descriptionMaxCharacters} chars   --fill: ${toFillPercent(descriptionCharacters, statsConfig.descriptionMaxCharacters)}%`)
  console.log(`SKILL.md     ${skillLines} / ${statsConfig.skillLinesBudget} lines   --fill: ${toFillPercent(skillLines, statsConfig.skillLinesBudget)}%`)
  const files = listSupportingFiles(skillDirectory)
  if (files.length === 0) {
    console.log('files        none')
  }
  let onDemandFiles = 0
  let onDemandLines = 0
  for (const file of files) {
    const isScript = statsConfig.scriptExtensions.includes(path.extname(file.relativePath).toLowerCase())
    if (!isScript) {
      onDemandFiles += 1
      onDemandLines += file.lines
    }
    console.log(`file         ${file.relativePath}  ${file.lines} lines${isScript ? '  (script: runs, never loaded)' : ''}`)
  }
  console.log(`on demand    ${onDemandFiles} file${onDemandFiles === 1 ? '' : 's'}, ${onDemandLines} lines (scripts excluded)`)
  return 0
}

// Replaces each match with only its newlines, so line numbers still point into the original file.
function blankOut(text, pattern) {
  return text.replace(pattern, function keepNewlines(match) { return match.replace(/[^\n]/g, ' ') })
}

function findAll(text, pattern) {
  const matches = []
  for (const match of text.matchAll(pattern)) {
    matches.push(match[0])
  }
  return matches
}

function readTemplateClasses(styleText) {
  const classes = new Set()
  for (const match of styleText.matchAll(/\.([a-zA-Z_][\w-]*)/g)) {
    classes.add(match[1])
  }
  return classes
}

function readAttribute(attributes, attributeName) {
  const match = new RegExp(`\\s${attributeName}="([^"]*)"`).exec(attributes)
  if (!match) {
    return null
  }
  return match[1]
}

function lineAt(text, index) {
  return text.slice(0, index).split('\n').length
}

function previewStatement(text, ruleStart) {
  const match = /class="rule-statement"[^>]*>([\s\S]*?)<\/(summary|h3)>/.exec(text.slice(ruleStart))
  if (!match) {
    return '(no .rule-statement)'
  }
  return match[1].replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim().slice(0, checkConfig.statementPreviewCharacters)
}

function checkFrame(page, template, errors) {
  if (checkConfig.forbiddenTagPattern.test(page)) {
    errors.push('remove <!doctype>, <html>, <head> and <body>: the publish step adds the skeleton')
  }
  const titleMatch = /<title>([^<]*)<\/title>/i.exec(page.slice(0, checkConfig.titleScanCharacters))
  if (!titleMatch || titleMatch[1].trim() === '') {
    errors.push('no <title> in the first 8KB')
  } else if (checkConfig.titleExplainerPattern.test(titleMatch[1]) || titleMatch[1].trim().split(/\s+/).length > checkConfig.titleMaxWords) {
    errors.push(`<title>${titleMatch[1]}</title> must be the skill's name only (the H1 from stats), at most ${checkConfig.titleMaxWords} words`)
  }
  const templateStyles = findAll(template, /<style>[\s\S]*?<\/style>/g)
  const pageStyles = findAll(page, /<style>[\s\S]*?<\/style>/g)
  if (pageStyles.length !== 1 || pageStyles[0] !== templateStyles[0]) {
    errors.push('the page needs exactly one <style>, byte-identical to template.html: copy it, never edit it')
  }
  const frameTags = findAll(template, /<link [^>]*>|<script[^>]*>[\s\S]*?<\/script>/g)
  for (const frameTag of frameTags) {
    if (!page.includes(frameTag)) {
      errors.push(`missing or changed template tag: ${frameTag.split('\n')[0].slice(0, checkConfig.tagPreviewCharacters)}`)
    }
  }
  const pageScripts = findAll(page, /<script[^>]*>[\s\S]*?<\/script>/g)
  for (const pageScript of pageScripts) {
    if (!frameTags.includes(pageScript)) {
      errors.push(`script not in template.html: ${pageScript.split('\n')[0].slice(0, checkConfig.tagPreviewCharacters)}`)
    }
  }
}

function checkBody(page, templateClasses, errors, warnings) {
  let body = blankOut(page, /<!--[\s\S]*?-->/g)
  body = blankOut(body, /<style>[\s\S]*?<\/style>|<script[^>]*>[\s\S]*?<\/script>/g)
  if (checkConfig.emojiPattern.test(body)) {
    warnings.push('emoji found: the template marks (✗ ✓ →) are the only symbols')
  }
  const stack = []
  for (const match of body.matchAll(/<(\/?)([a-zA-Z][\w-]*)([^>]*)>/g)) {
    const isClosing = match[1] === '/'
    const tagName = match[2].toLowerCase()
    const attributes = match[3]
    const line = lineAt(body, match.index)
    if (isClosing) {
      const open = stack.pop()
      if (!open) {
        errors.push(`line ${line}: stray </${tagName}>`)
        return
      }
      if (open.tagName !== tagName) {
        errors.push(`line ${open.line}: <${open.tagName}> is closed by </${tagName}> on line ${line} (unescaped < in code? write &lt;)`)
        return
      }
      if (open.classes.includes('compare') && (!open.hasBad || !open.hasGood)) {
        errors.push(`line ${open.line}: .compare needs a .compare-row.bad and a .compare-row.good`)
      }
      if (open.classes.includes('rule') && !open.hasExample) {
        warnings.push(`line ${open.line}: rule without example: "${previewStatement(body, open.start)}" (gap report)`)
      }
      continue
    }
    const classText = readAttribute(attributes, 'class')
    const classes = []
    if (classText !== null) {
      for (const className of classText.split(/\s+/)) {
        if (className !== '') {
          classes.push(className)
        }
      }
    }
    for (const className of classes) {
      if (!templateClasses.has(className) && !checkConfig.languageClassPattern.test(className)) {
        errors.push(`line ${line}: class "${className}" is not in template.html`)
      }
    }
    const styleText = readAttribute(attributes, 'style')
    if (styleText !== null && !checkConfig.fillStylePattern.test(styleText.trim())) {
      errors.push(`line ${line}: style="${styleText}" (only style="--fill: N%" on a .load-bar is allowed)`)
    }
    for (const ancestor of stack) {
      if (ancestor.classes.includes('compare') && classes.includes('bad')) {
        ancestor.hasBad = true
      }
      if (ancestor.classes.includes('compare') && classes.includes('good')) {
        ancestor.hasGood = true
      }
      for (const exampleClass of checkConfig.exampleClasses) {
        if (ancestor.classes.includes('rule') && classes.includes(exampleClass)) {
          ancestor.hasExample = true
        }
      }
    }
    if (checkConfig.voidTags.includes(tagName) || attributes.endsWith('/')) {
      continue
    }
    stack.push({ tagName: tagName, classes: classes, line: line, start: match.index, hasBad: false, hasGood: false, hasExample: false })
  }
  for (const open of stack) {
    errors.push(`line ${open.line}: <${open.tagName}> is never closed (unescaped < in code? write &lt;)`)
  }
  checkAnchors(body, errors)
}

// Every sidebar link (href="#x") needs an element with id="x".
function checkAnchors(body, errors) {
  const ids = new Set()
  for (const match of body.matchAll(/\sid="([^"]+)"/g)) {
    if (ids.has(match[1])) {
      errors.push(`line ${lineAt(body, match.index)}: duplicate id="${match[1]}"`)
    }
    ids.add(match[1])
  }
  for (const match of body.matchAll(/\shref="#([^"]+)"/g)) {
    if (!ids.has(match[1])) {
      errors.push(`line ${lineAt(body, match.index)}: href="#${match[1]}" has no element with that id`)
    }
  }
}

function checkPage(pagePath) {
  if (!fs.existsSync(pagePath)) {
    console.log(`ERROR: ${pagePath} not found`)
    return 1
  }
  const page = readText(pagePath)
  const template = readText(checkConfig.templatePath)
  const templateStyle = findAll(template, /<style>[\s\S]*?<\/style>/g)[0]
  const errors = []
  const warnings = []
  checkFrame(page, template, errors)
  checkBody(page, readTemplateClasses(templateStyle), errors, warnings)
  for (const error of errors) {
    console.log(`ERROR: ${error}`)
  }
  for (const warning of warnings) {
    console.log(`WARN:  ${warning}`)
  }
  if (errors.length === 0 && warnings.length === 0) {
    console.log('OK')
  }
  return errors.length === 0 ? 0 : 1
}

function main(argumentsList) {
  const command = argumentsList[0]
  const target = argumentsList[1]
  if (!target || (command !== 'stats' && command !== 'check')) {
    console.log('usage: node skill_page.mjs stats <skill-dir> | check <page.html>')
    return 2
  }
  if (command === 'stats') {
    return printStats(target)
  }
  return checkPage(target)
}

process.exitCode = main(process.argv.slice(2))
