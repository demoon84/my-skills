#!/usr/bin/env node

import path from "node:path";
import { fileURLToPath } from "node:url";

import { createConfig } from "../config.mjs";
import {
  allowedTargets,
  getInstallState,
  scanSkillsDir,
  validateSkill
} from "../lib/skills.mjs";
import { installSkill, uninstallSkill, writeManifests } from "../lib/skills-install.mjs";

function parseArgs(argv) {
  const args = {
    _: [],
    tools: null,
    scope: "global",
    mode: "link",
    force: false,
    dryRun: false
  };

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    const next = argv[i + 1];
    switch (token) {
      case "--tools":
        if (next) {
          args.tools = next.split(",").map((t) => t.trim()).filter(Boolean);
          i += 1;
        }
        break;
      case "--project":
        args.scope = "project";
        break;
      case "--copy":
        args.mode = "copy";
        break;
      case "--force":
        args.force = true;
        break;
      case "--dry-run":
        args.dryRun = true;
        break;
      case "--all":
        args._all = true;
        break;
      default:
        args._.push(token);
    }
  }
  return args;
}

function printHelp() {
  console.log(`myskills — installer

Usage:
  install-skills.mjs <command> [options]

Commands:
  list                         List skills discovered in the source directory
  status [name]                Show install state per tool
  install [name]|--all         Install one skill, or all
  uninstall <name>             Remove installed symlinks
  validate [name]              Validate skill frontmatter + files

Options:
  --tools codex                Filter target tools (Codex only)
  --project                    Install into project scope (.agents/skills)
  --copy                       Copy files instead of symlinking
  --force                      Overwrite existing entries
  --dry-run                    Show what would happen without writing
`);
}

function buildConfig(tools) {
  const config = createConfig();
  if (tools) {
    const supportedTargets = allowedTargets();
    config.skills = {
      ...config.skills,
      targets: tools.filter((tool) => supportedTargets.includes(tool))
    };
  }
  return config;
}

function runList(skillsConfig) {
  const skills = scanSkillsDir(skillsConfig.sourceDir);
  if (!skills.length) {
    console.log(`(no skills found under ${skillsConfig.sourceDir})`);
    return 0;
  }

  for (const skill of skills) {
    console.log(`- ${skill.name}: ${skill.description || "(no description)"} [targets: ${skill.targets.join(",")}]`);
  }
  return 0;
}

function runStatus(skillsConfig, skillName, scope, cwd) {
  const skills = scanSkillsDir(skillsConfig.sourceDir);
  const filtered = skillName ? skills.filter((s) => s.name === skillName) : skills;

  if (!filtered.length) {
    console.log(`(no matching skills)`);
    return 0;
  }

  for (const skill of filtered) {
    console.log(`\n${skill.name}`);
    const state = getInstallState(skill, { skillsConfig, scope, cwd });
    for (const [tool, info] of Object.entries(state)) {
      console.log(`  ${tool}: ${info.status} → ${info.targetPath}`);
    }
  }
  return 0;
}

function runValidate(skillsConfig, skillName) {
  const skills = scanSkillsDir(skillsConfig.sourceDir);
  const filtered = skillName ? skills.filter((s) => s.name === skillName) : skills;

  if (!filtered.length) {
    console.log(`(no matching skills)`);
    return 1;
  }

  let anyIssues = false;
  for (const skill of filtered) {
    const issues = validateSkill(skill);
    if (issues.length) {
      anyIssues = true;
      console.log(`✗ ${skill.name}`);
      for (const issue of issues) console.log(`  - ${issue}`);
    } else {
      console.log(`✓ ${skill.name}`);
    }
  }
  return anyIssues ? 1 : 0;
}

function runInstall(skillsConfig, args, cwd) {
  const skills = scanSkillsDir(skillsConfig.sourceDir);
  let selected;

  if (args._all) {
    selected = skills;
  } else if (args._.length >= 2) {
    const names = args._.slice(1);
    selected = skills.filter((s) => names.includes(s.name));
    const missing = names.filter((name) => !selected.find((s) => s.name === name));
    if (missing.length) {
      console.error(`Unknown skills: ${missing.join(", ")}`);
      return 1;
    }
  } else {
    console.error("Specify a skill name or use --all");
    return 1;
  }

  if (!selected.length) {
    console.log("(nothing to install)");
    return 0;
  }

  let failed = false;
  for (const skill of selected) {
    const result = installSkill(skill, {
      skillsConfig,
      scope: args.scope,
      cwd,
      mode: args.mode,
      force: args.force,
      dryRun: args.dryRun
    });

    if (!result.ok && result.issues.length) {
      failed = true;
      console.log(`✗ ${skill.name} (validation)`);
      for (const issue of result.issues) console.log(`  - ${issue}`);
      continue;
    }

    console.log(`${result.ok ? "✓" : "✗"} ${skill.name}`);
    for (const [tool, info] of Object.entries(result.results)) {
      console.log(`  ${tool}: ${info.action} ${info.targetPath}${info.message ? " — " + info.message : ""}`);
      if (!info.ok) failed = true;
    }
  }

  const manifests = writeManifests(selected, {
    skillsConfig,
    scope: args.scope,
    cwd,
    dryRun: args.dryRun
  });
  console.log("\nmanifests:");
  for (const [tool, info] of Object.entries(manifests)) {
    console.log(`  ${tool}: ${info.action || info.message || "ok"} → ${info.target || "-"}`);
  }

  return failed ? 1 : 0;
}

function runUninstall(skillsConfig, args, cwd) {
  const name = args._[1];
  if (!name) {
    console.error("Specify a skill name to uninstall");
    return 1;
  }

  const skills = scanSkillsDir(skillsConfig.sourceDir);
  const skill = skills.find((s) => s.name === name);
  if (!skill) {
    console.error(`Unknown skill: ${name}`);
    return 1;
  }

  const result = uninstallSkill(skill, {
    skillsConfig,
    scope: args.scope,
    cwd,
    dryRun: args.dryRun
  });

  console.log(skill.name);
  for (const [tool, info] of Object.entries(result.results)) {
    console.log(`  ${tool}: ${info.action} ${info.targetPath}${info.message ? " — " + info.message : ""}`);
  }
  return 0;
}

export function runSkillsCli(argv = process.argv.slice(2)) {
  const parsed = parseArgs(argv);
  const command = parsed._[0];
  const config = buildConfig(parsed.tools);
  const cwd = process.cwd();

  if (!command || command === "help" || command === "--help" || command === "-h") {
    printHelp();
    return 0;
  }

  switch (command) {
    case "list":
      return runList(config.skills);
    case "status":
      return runStatus(config.skills, parsed._[1] || null, parsed.scope, cwd);
    case "validate":
      return runValidate(config.skills, parsed._[1] || null);
    case "install":
      return runInstall(config.skills, parsed, cwd);
    case "uninstall":
      return runUninstall(config.skills, parsed, cwd);
    default:
      console.error(`Unknown command: ${command}`);
      printHelp();
      return 1;
  }
}

function isDirectExecution() {
  const entryPath = process.argv[1];
  if (!entryPath) {
    return false;
  }

  return path.resolve(fileURLToPath(import.meta.url)) === path.resolve(entryPath);
}

if (isDirectExecution()) {
  const code = runSkillsCli();
  process.exit(code);
}
