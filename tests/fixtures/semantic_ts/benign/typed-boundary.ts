import type { OrderStatus } from "../src/domain";

export function publishStatus(status: OrderStatus): OrderStatus {
  return status;
}
