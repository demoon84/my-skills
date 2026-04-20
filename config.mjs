import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
const homeDir = os.homedir();
const DEFAULT_TARGETS = ["codex"];

function parseTargetsEnv(value) {
  if (!value || typeof value !== "string") {
    return [...DEFAULT_TARGETS];
  }
  const targets = value
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter((entry) => DEFAULT_TARGETS.includes(entry));
  return targets.length ? targets : [...DEFAULT_TARGETS];
}

export const skillsConfig = {
  sourceDir: process.env.MYSKILLS_SOURCE_DIR || path.join(repoRoot, "skills"),
  targets: parseTargetsEnv(process.env.MYSKILLS_TARGETS),
  globalDirs: {
    codex: path.join(homeDir, ".codex", "skills")
  },
  projectDirs: {
    codex: path.join(".agents", "skills")
  },
  manifestTargets: {
    codex: path.join(homeDir, ".codex", "hooks.json")
  }
};

export function createConfig(overrides = {}) {
  return {
    skills: {
      ...skillsConfig,
      ...(overrides.skills || {}),
      globalDirs: {
        ...skillsConfig.globalDirs,
        ...((overrides.skills && overrides.skills.globalDirs) || {})
      },
      projectDirs: {
        ...skillsConfig.projectDirs,
        ...((overrides.skills && overrides.skills.projectDirs) || {})
      },
      manifestTargets: {
        ...skillsConfig.manifestTargets,
        ...((overrides.skills && overrides.skills.manifestTargets) || {})
      }
    }
  };
}
