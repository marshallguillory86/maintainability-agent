const labels = ["create", "refresh", "revoke"];

export function menu(): string {
  return labels.map((label) => `Action: ${label}`).join(", ");
}
