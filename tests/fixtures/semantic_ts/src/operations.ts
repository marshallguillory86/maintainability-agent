export type SessionCapability = "create" | "refresh" | "revoke";

export function dispatch(operation: string): number {
  if (operation === "create") return 1;
  if (operation === "refresh") return 2;
  if (operation === "revoke") return 3;
  return 0;
}

export function canRun(operation: string): boolean {
  return ["create", "refresh", "revoke"].includes(operation);
}

export function describe(operation: string): string {
  const descriptions: Record<string, string> = {
    create: "Create a session",
    refresh: "Refresh a session",
    revoke: "Revoke a session",
  };
  return descriptions[operation] ?? "Unknown operation";
}
