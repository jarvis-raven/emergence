import type { HookHandler } from "../../src/hooks/hooks.js";
import fs from "node:fs/promises";
import path from "node:path";

/**
 * Find drives-state.json by searching config-aware paths.
 * No hardcoded paths — works for any Emergence agent.
 */
async function findDrivesState(workspaceDir: string): Promise<string | null> {
  // 1. Check EMERGENCE_CONFIG env var
  const envConfig = process.env.EMERGENCE_CONFIG;
  if (envConfig) {
    const statePath = await resolveStateFromConfig(envConfig);
    if (statePath) return statePath;
  }

  // 2. Check workspace/emergence.json
  const workspaceConfig = path.join(workspaceDir, "emergence.json");
  const statePath = await resolveStateFromConfig(workspaceConfig);
  if (statePath) return statePath;

  // 3. Common OpenClaw layout: workspace/../state/drives-state.json
  const openclawState = path.resolve(workspaceDir, "..", "state", "drives-state.json");
  if (await fileExists(openclawState)) return openclawState;

  // 4. Default Emergence layout: workspace/.emergence/state/drives-state.json
  const defaultState = path.join(workspaceDir, ".emergence", "state", "drives-state.json");
  if (await fileExists(defaultState)) return defaultState;

  return null;
}

/**
 * Read emergence.json config and resolve the state directory path.
 */
async function resolveStateFromConfig(configPath: string): Promise<string | null> {
  try {
    const raw = await fs.readFile(configPath, "utf-8");
    // Strip comments (// style) before parsing
    const clean = raw.replace(/^\s*\/\/.*$/gm, "");
    const config = JSON.parse(clean);
    const paths = config?.paths ?? {};
    const workspace = paths.workspace ?? ".";
    const stateDir = paths.state ?? ".emergence/state";

    const configDir = path.dirname(configPath);
    const resolvedWorkspace = path.resolve(configDir, workspace);
    const resolvedState = path.resolve(resolvedWorkspace, stateDir, "drives-state.json");

    if (await fileExists(resolvedState)) return resolvedState;
  } catch {
    // Config doesn't exist or isn't valid — try next method
  }
  return null;
}

async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Format drives state as a concise markdown snippet for context injection.
 */
function formatDrivesForContext(data: any): string {
  const drives = data?.drives ?? {};
  const lastTick = data?.last_tick ?? data?.last_updated ?? "unknown";
  const driveNames = Object.keys(drives);

  if (driveNames.length === 0) return "";

  const lines: string[] = [
    "## Drives State",
    `*${driveNames.length} drives, updated ${lastTick}*`,
    "",
  ];

  // Sort by ratio descending (highest pressure first)
  const sorted = driveNames
    .map((name) => {
      const d = drives[name];
      const pressure = d?.pressure ?? 0;
      const threshold = d?.threshold ?? 1;
      const ratio = threshold > 0 ? pressure / threshold : 0;
      const description = d?.description ?? "";
      return { name, pressure, threshold, ratio, description, status: d?.status };
    })
    .sort((a, b) => b.ratio - a.ratio);

  // Flag triggered drives prominently
  const triggered = sorted.filter((d) => d.ratio >= 1.0);
  if (triggered.length > 0) {
    lines.push("**🔥 Triggered:**");
    for (const d of triggered) {
      lines.push(`- **${d.name}** at ${Math.round(d.ratio * 100)}% (${d.pressure.toFixed(1)}/${d.threshold})`);
    }
    lines.push("");
  }

  // Show all drives compactly
  for (const d of sorted) {
    const bar = d.ratio >= 1.0 ? "🔴" : d.ratio >= 0.8 ? "🟡" : "🟢";
    const desc = d.description ? ` — ${d.description}` : "";
    lines.push(`${bar} ${d.name}: ${d.pressure.toFixed(1)}/${d.threshold} (${Math.round(d.ratio * 100)}%)${desc}`);
  }

  return lines.join("\n");
}

const handler: HookHandler = async (event) => {
  // Only handle agent:bootstrap events
  if (event.type !== "agent" || event.action !== "bootstrap") return;

  const context = event.context;
  const workspaceDir = context.workspaceDir;

  if (!workspaceDir || !Array.isArray(context.bootstrapFiles)) return;

  // Find drives-state.json
  const statePath = await findDrivesState(workspaceDir);
  if (!statePath) return; // No Emergence drives — silently skip

  // Read and parse
  let data: any;
  try {
    const raw = await fs.readFile(statePath, "utf-8");
    data = JSON.parse(raw);
  } catch {
    return; // File unreadable — skip silently
  }

  // Format and inject
  const content = formatDrivesForContext(data);
  if (!content) return;

  // Append as a new bootstrap file
  context.bootstrapFiles.push({
    name: "DRIVES.md",
    content,
    missing: false,
  });
};

export default handler;
