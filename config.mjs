import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
const homeDir = os.homedir();

function parseTargetsEnv(value) {
  if (!value || typeof value !== "string") {
    return ["claude", "codex", "gemini"];
  }
  return value
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean);
}

export const skillsConfig = {
  sourceDir: process.env.MYSKILLS_SOURCE_DIR || path.join(repoRoot, "skills"),
  targets: parseTargetsEnv(process.env.MYSKILLS_TARGETS),
  globalDirs: {
    claude: path.join(homeDir, ".claude", "skills"),
    codex: path.join(homeDir, ".codex", "skills"),
    gemini: path.join(homeDir, ".gemini", "skills")
  },
  projectDirs: {
    claude: path.join(".claude", "skills"),
    codex: path.join(".agents", "skills"),
    gemini: path.join(".agents", "skills")
  },
  manifestTargets: {
    claude: path.join(homeDir, ".claude", "plugins", "myskills", "plugin.json"),
    codex: path.join(homeDir, ".codex", "hooks.json"),
    gemini: path.join(homeDir, ".gemini", "hooks.json")
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
