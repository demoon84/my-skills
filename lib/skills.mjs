import fs from "node:fs";
import path from "node:path";

const ALLOWED_TARGETS = ["claude", "codex", "gemini"];
const ALLOWED_HOOKS = ["session_start", "stop", "pre_tool_use", "post_tool_use"];

export class SkillValidationError extends Error {
  constructor(message, { skillName, skillPath, issues = [] } = {}) {
    super(message);
    this.name = "SkillValidationError";
    this.skillName = skillName || null;
    this.skillPath = skillPath || null;
    this.issues = issues;
  }
}

function parseFrontmatterBlock(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) {
    return { frontmatter: {}, body: text };
  }

  const rawFrontmatter = match[1];
  const body = match[2] || "";
  const frontmatter = parseYamlSubset(rawFrontmatter);
  return { frontmatter, body };
}

function parseYamlSubset(text) {
  const result = {};
  const lines = text.split(/\r?\n/);
  let currentKey = null;
  let currentObject = null;

  for (const rawLine of lines) {
    if (!rawLine.trim() || rawLine.trim().startsWith("#")) {
      continue;
    }

    const indentMatch = rawLine.match(/^( *)/);
    const indent = indentMatch ? indentMatch[1].length : 0;
    const line = rawLine.slice(indent);

    if (indent === 0) {
      currentKey = null;
      currentObject = null;

      const mapMatch = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
      if (!mapMatch) {
        continue;
      }
      const key = mapMatch[1];
      const rawValue = mapMatch[2].trim();

      if (rawValue === "") {
        result[key] = {};
        currentKey = key;
        currentObject = result[key];
      } else if (rawValue.startsWith("[") && rawValue.endsWith("]")) {
        result[key] = parseInlineArray(rawValue);
      } else {
        result[key] = coerceScalar(rawValue);
      }
      continue;
    }

    if (currentKey && currentObject && typeof currentObject === "object") {
      const mapMatch = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
      if (!mapMatch) {
        continue;
      }
      const key = mapMatch[1];
      const rawValue = mapMatch[2].trim();

      if (rawValue.startsWith("[") && rawValue.endsWith("]")) {
        currentObject[key] = parseInlineArray(rawValue);
      } else {
        currentObject[key] = coerceScalar(rawValue);
      }
    }
  }

  return result;
}

function parseInlineArray(text) {
  const inner = text.slice(1, -1).trim();
  if (!inner) {
    return [];
  }
  return inner
    .split(",")
    .map((item) => coerceScalar(item.trim()))
    .filter((item) => item !== "" && item !== undefined && item !== null);
}

function coerceScalar(value) {
  if (value === undefined || value === null) {
    return value;
  }
  const trimmed = String(value).trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (trimmed === "null") return null;
  return trimmed;
}

export function parseSkillFile(skillMdPath) {
  const text = fs.readFileSync(skillMdPath, "utf8");
  return parseFrontmatterBlock(text);
}

export function loadSkill(skillDir) {
  const skillMdPath = path.join(skillDir, "SKILL.md");
  if (!fs.existsSync(skillMdPath)) {
    return null;
  }

  const { frontmatter, body } = parseSkillFile(skillMdPath);
  const folderName = path.basename(skillDir);

  const targets = Array.isArray(frontmatter.targets) && frontmatter.targets.length
    ? frontmatter.targets.map((entry) => String(entry).toLowerCase())
    : [...ALLOWED_TARGETS];

  const hooks = {};
  if (frontmatter.hooks && typeof frontmatter.hooks === "object") {
    for (const [event, script] of Object.entries(frontmatter.hooks)) {
      if (typeof script === "string" && script.trim()) {
        hooks[event] = script.trim();
      }
    }
  }

  return {
    name: frontmatter.name || folderName,
    description: frontmatter.description || "",
    folderName,
    path: skillDir,
    skillMdPath,
    targets,
    hooks,
    metadata: frontmatter.metadata && typeof frontmatter.metadata === "object"
      ? frontmatter.metadata
      : {},
    body
  };
}

export function scanSkillsDir(sourceDir) {
  if (!fs.existsSync(sourceDir)) {
    return [];
  }

  const entries = fs.readdirSync(sourceDir, { withFileTypes: true });
  const skills = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    if (entry.name.startsWith("_") || entry.name.startsWith(".")) continue;

    const skillDir = path.join(sourceDir, entry.name);
    const skill = loadSkill(skillDir);
    if (skill) {
      skills.push(skill);
    }
  }

  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

export function validateSkill(skill) {
  const issues = [];

  if (!skill.name) {
    issues.push("missing `name` in frontmatter");
  } else if (skill.name !== skill.folderName) {
    issues.push(`frontmatter name "${skill.name}" does not match folder "${skill.folderName}"`);
  }

  if (!skill.description) {
    issues.push("missing `description` in frontmatter");
  }

  for (const target of skill.targets) {
    if (!ALLOWED_TARGETS.includes(target)) {
      issues.push(`unknown target "${target}" (allowed: ${ALLOWED_TARGETS.join(", ")})`);
    }
  }

  for (const [event, script] of Object.entries(skill.hooks)) {
    if (!ALLOWED_HOOKS.includes(event)) {
      issues.push(`unknown hook event "${event}" (allowed: ${ALLOWED_HOOKS.join(", ")})`);
      continue;
    }
    const scriptPath = path.resolve(skill.path, script);
    if (!fs.existsSync(scriptPath)) {
      issues.push(`hook "${event}" references missing script: ${script}`);
    }
  }

  return issues;
}

export function resolveInstallTargets(skill, { skillsConfig, scope = "global", cwd = process.cwd() }) {
  const baseDirs = scope === "project" ? skillsConfig.projectDirs : skillsConfig.globalDirs;
  const targets = {};

  for (const tool of skill.targets) {
    if (!skillsConfig.targets.includes(tool)) continue;
    if (!baseDirs[tool]) continue;

    const base = scope === "project" ? path.resolve(cwd, baseDirs[tool]) : baseDirs[tool];
    targets[tool] = path.join(base, skill.name);
  }

  return targets;
}

export function getInstallState(skill, options) {
  const targets = resolveInstallTargets(skill, options);
  const state = {};

  for (const [tool, targetPath] of Object.entries(targets)) {
    let status = "missing";
    let linkTarget = null;
    let matches = false;

    if (fs.existsSync(targetPath)) {
      try {
        const lstat = fs.lstatSync(targetPath);
        if (lstat.isSymbolicLink()) {
          linkTarget = fs.readlinkSync(targetPath);
          const resolved = path.resolve(path.dirname(targetPath), linkTarget);
          matches = resolved === path.resolve(skill.path);
          status = matches ? "linked" : "linked-elsewhere";
        } else {
          status = "exists-other";
        }
      } catch {
        status = "unknown";
      }
    }

    state[tool] = { targetPath, status, linkTarget, matches };
  }

  return state;
}

export function allowedTargets() {
  return [...ALLOWED_TARGETS];
}

export function allowedHooks() {
  return [...ALLOWED_HOOKS];
}
