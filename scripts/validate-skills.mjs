#!/usr/bin/env node

import { runSkillsCli } from "./install-skills.mjs";

export function runValidate(argv = process.argv.slice(2)) {
  return runSkillsCli(["validate", ...argv]);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  process.exit(runValidate());
}
