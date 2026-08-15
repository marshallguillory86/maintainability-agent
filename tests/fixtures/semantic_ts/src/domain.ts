export type OrderStatus = "pending" | "paid" | "cancelled";

declare const customerIdBrand: unique symbol;
export type CustomerId = string & { readonly [customerIdBrand]: true };

export function acceptStatus(status: OrderStatus): OrderStatus {
  return status;
}

export function looksLikeCustomerId(value: string): boolean {
  return /^customer-[0-9]+$/.test(value);
}

export function normalizeCustomerId(value: string): CustomerId {
  return value.trim() as CustomerId;
}
