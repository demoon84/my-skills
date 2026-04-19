#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { createConfig } from "../config.mjs";

function printHelp() {
  console.log(`myskills new <name> [--force]

Scaffolds a new skill folder from skills/_template.

Options:
  --force    Overwrite an existing skill folder of the same name
`);
}

export function runScaffold(argv = process.argv.slice(2)) {
  let force = false;
  const positional = [];
  for (const token of argv) {
    if (token === "--force") force = true;
    else if (token === "--help" || token === "-h") {
      printHelp();
      return 0;
    } else positional.push(token);
  }

  const name = positional[0];
  if (!name) {
    printHelp();
    return 1;
  }

  if (!/^[a-z0-9][a-z0-9-]*$/.test(name)) {
    console.error("Skill name must be lowercase letters, digits, hyphens (e.g. my-skill)");
    return 1;
  }

  const config = createConfig();
  const templateDir = path.join(config.skills.sourceDir, "_template");
  const targetDir = path.join(config.skills.sourceDir, name);

  if (!fs.existsSync(templateDir)) {
    console.error(`Template not found at ${templateDir}`);
    return 1;
  }

  if (fs.existsSync(targetDir)) {
    if (!force) {
      console.error(`Skill already exists: ${targetDir} (use --force to overwrite)`);
      return 1;
    }
    fs.rmSync(targetDir, { recursive: true, force: true });
  }

  copyRecursive(templateDir, targetDir);
  substituteName(targetDir, name);

  console.log(`Created ${targetDir}`);
  console.log("Next: edit SKILL.md, then run:");
  console.log(`  node scripts/install-skills.mjs validate ${name}`);
  console.log(`  node scripts/install-skills.mjs install ${name}`);
  return 0;
}

function copyRecursive(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyRecursive(from, to);
    } else {
      fs.copyFileSync(from, to);
    }
  }
}

function substituteName(dir, name) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      substituteName(full, name);
      continue;
    }
    if (!entry.isFile()) continue;
    try {
      const text = fs.readFileSync(full, "utf8");
      if (text.includes("__SKILL_NAME__")) {
        fs.writeFileSync(full, text.replaceAll("__SKILL_NAME__", name), "utf8");
      }
    } catch {
      // binary file, skip
    }
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const code = runScaffold();
  process.exit(code);
}
