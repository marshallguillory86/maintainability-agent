import {
  looksLikeCustomerId,
  normalizeCustomerId,
} from "./domain";

declare function fetchCustomer(id: string): unknown;

export function loadCustomer(customerId: string): unknown {
  if (!looksLikeCustomerId(customerId)) {
    throw new Error("invalid customer id");
  }
  const normalized = normalizeCustomerId(customerId);
  return fetchCustomer(normalized);
}
