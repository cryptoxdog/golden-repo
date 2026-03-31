export type SignatureAlgorithm = "hmac-sha256" | "ed25519";
export interface TenantContext { actor: string; on_behalf_of: string; originator: string; org_id: string; user_id?: string | null; }
export interface ExecuteOptions { destinationNode: string; sourceNode?: string; replyTo?: string; timeoutMs?: number; idempotencyKey?: string | null; }
