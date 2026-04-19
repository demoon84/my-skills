import fs from "node:fs";
import path from "node:path";
import {
  getInstallState,
  resolveInstallTargets,
  scanSkillsDir,
  validateSkill
} from "./skills.mjs";

const MANIFEST_MARKER = "myskills";

function pathExists(p) {
  try {
    fs.lstatSync(p);
    return true;
  } catch {
    return false;
  }
}

export function installSkill(skill, {
  skillsConfig,
  scope = "global",
  cwd = process.cwd(),
  mode = "link",
  force = false,
  dryRun = false
} = {}) {
  const issues = validateSkill(skill);
  if (issues.length) {
    return {
      skill: skill.name,
      ok: false,
      issues,
      results: {}
    };
  }

  const targets = resolveInstallTargets(skill, { skillsConfig, scope, cwd });
  const results = {};

  for (const [tool, targetPath] of Object.entries(targets)) {
    results[tool] = installToTarget(skill, targetPath, { mode, force, dryRun });
  }

  return {
    skill: skill.name,
    ok: Object.values(results).every((r) => r.ok || r.skipped),
    issues: [],
    results
  };
}

function installToTarget(skill, targetPath, { mode, force, dryRun }) {
  const parent = path.dirname(targetPath);

  if (pathExists(targetPath)) {
    try {
      const lstat = fs.lstatSync(targetPath);
      if (lstat.isSymbolicLink()) {
        const existing = fs.readlinkSync(targetPath);
        const resolved = path.resolve(path.dirname(targetPath), existing);
        if (resolved === path.resolve(skill.path)) {
          return { ok: true, action: "unchanged", targetPath };
        }
        const linkTargetExists = fs.existsSync(targetPath);
        if (!force && linkTargetExists) {
          return {
            ok: false,
            action: "conflict-link",
            targetPath,
            message: `existing symlink at ${targetPath} → ${existing} (use --force to replace)`
          };
        }
        // Broken symlink (target missing) or --force → fall through to replace
      } else if (!force) {
        return {
          ok: false,
          action: "conflict-file",
          targetPath,
          message: `existing file/dir at ${targetPath} (use --force to replace)`
        };
      }
    } catch (error) {
      return { ok: false, action: "stat-error", targetPath, message: error.message };
    }
  }

  if (dryRun) {
    return {
      ok: true,
      action: mode === "copy" ? "would-copy" : "would-link",
      targetPath
    };
  }

  fs.mkdirSync(parent, { recursive: true });

  if (pathExists(targetPath)) {
    removePath(targetPath);
  }

  if (mode === "copy") {
    copyRecursive(skill.path, targetPath);
    return { ok: true, action: "copied", targetPath };
  }

  fs.symlinkSync(skill.path, targetPath, "dir");
  return { ok: true, action: "linked", targetPath };
}

export function uninstallSkill(skill, {
  skillsConfig,
  scope = "global",
  cwd = process.cwd(),
  dryRun = false
} = {}) {
  const targets = resolveInstallTargets(skill, { skillsConfig, scope, cwd });
  const results = {};

  for (const [tool, targetPath] of Object.entries(targets)) {
    if (!pathExists(targetPath)) {
      results[tool] = { ok: true, action: "absent", targetPath };
      continue;
    }
    try {
      const lstat = fs.lstatSync(targetPath);
      if (lstat.isSymbolicLink()) {
        const existing = fs.readlinkSync(targetPath);
        const resolved = path.resolve(path.dirname(targetPath), existing);
        if (resolved !== path.resolve(skill.path)) {
          results[tool] = {
            ok: false,
            action: "foreign-link",
            targetPath,
            message: `symlink points elsewhere: ${existing}`
          };
          continue;
        }
      } else {
        results[tool] = {
          ok: false,
          action: "not-a-link",
          targetPath,
          message: "refusing to delete non-symlink entry"
        };
        continue;
      }
    } catch (error) {
      results[tool] = { ok: false, action: "stat-error", targetPath, message: error.message };
      continue;
    }

    if (dryRun) {
      results[tool] = { ok: true, action: "would-remove", targetPath };
      continue;
    }

    removePath(targetPath);
    results[tool] = { ok: true, action: "removed", targetPath };
  }

  return { skill: skill.name, results };
}

function removePath(target) {
  try {
    const lstat = fs.lstatSync(target);
    if (lstat.isSymbolicLink() || lstat.isFile()) {
      fs.unlinkSync(target);
    } else {
      fs.rmSync(target, { recursive: true, force: true });
    }
  } catch {
    // noop
  }
}

function copyRecursive(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyRecursive(from, to);
    } else if (entry.isSymbolicLink()) {
      fs.symlinkSync(fs.readlinkSync(from), to);
    } else {
      fs.copyFileSync(from, to);
    }
  }
}

export function generateManifest(tool, skills, { skillsConfig, scope = "global", cwd = process.cwd() }) {
  const relevantSkills = skills.filter((skill) => skill.targets.includes(tool));
  return buildUnifiedManifest(tool, relevantSkills, skillsConfig, scope, cwd);
}

function resolveHookScript(skill, scriptRel, { skillsConfig, scope, cwd }) {
  const targets = resolveInstallTargets(skill, { skillsConfig, scope, cwd });
  return targets;
}

// Claude / Codex / Gemini all use the same lifecycle event names
// (SessionStart / Stop / PreToolUse / PostToolUse / UserPromptSubmit) and the
// same JSON manifest shape, because Codex and Gemini adopted Claude's hook contract.
function buildUnifiedManifest(tool, skills, skillsConfig, scope, cwd) {
  const manifest = {
    $marker: MANIFEST_MARKER,
    name: "myskills",
    version: "0.1.0",
    description: "Generated by myskills — do not hand-edit.",
    hooks: {}
  };

  const buckets = {
    SessionStart: [],
    Stop: [],
    PreToolUse: [],
    PostToolUse: []
  };

  for (const skill of skills) {
    const targets = resolveHookScript(skill, null, { skillsConfig, scope, cwd });
    const skillInstallPath = targets[tool];
    if (!skillInstallPath) continue;

    for (const [event, scriptRel] of Object.entries(skill.hooks)) {
      const eventKey = mapHookEvent(event);
      if (!eventKey) continue;
      buckets[eventKey].push({
        hooks: [
          {
            type: "command",
            command: path.join(skillInstallPath, scriptRel),
            timeout: 30
          }
        ]
      });
    }
  }

  for (const [event, entries] of Object.entries(buckets)) {
    if (entries.length) {
      manifest.hooks[event] = entries;
    }
  }

  return {
    content: JSON.stringify(manifest, null, 2),
    format: "json"
  };
}

function mapHookEvent(event) {
  switch (event) {
    case "session_start":
      return "SessionStart";
    case "stop":
      return "Stop";
    case "pre_tool_use":
      return "PreToolUse";
    case "post_tool_use":
      return "PostToolUse";
    default:
      return null;
  }
}

export function writeManifests(skills, { skillsConfig, scope = "global", cwd = process.cwd(), dryRun = false }) {
  const results = {};
  for (const tool of skillsConfig.targets) {
    const manifest = generateManifest(tool, skills, { skillsConfig, scope, cwd });
    if (!manifest) continue;

    const target = skillsConfig.manifestTargets[tool];
    if (!target) {
      results[tool] = { ok: false, message: "no manifest target configured" };
      continue;
    }

    if (dryRun) {
      results[tool] = { ok: true, action: "would-write", target };
      continue;
    }

    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, manifest.content, "utf8");
    results[tool] = { ok: true, action: "written", target };
  }
  return results;
}

export function installAll({
  skillsConfig,
  scope = "global",
  cwd = process.cwd(),
  mode = "link",
  force = false,
  dryRun = false,
  onlyNames = null
}) {
  const all = scanSkillsDir(skillsConfig.sourceDir);
  const selected = onlyNames
    ? all.filter((skill) => onlyNames.includes(skill.name))
    : all;

  const installs = selected.map((skill) =>
    installSkill(skill, { skillsConfig, scope, cwd, mode, force, dryRun })
  );

  const manifests = writeManifests(selected, { skillsConfig, scope, cwd, dryRun });

  return { installs, manifests, total: selected.length };
}
