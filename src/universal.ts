import { acceptStatus } from "./domain";

export function publish(raw: string): void {
  if (raw.length === 0) {
    return;
  }

  acceptStatus(raw);
}
