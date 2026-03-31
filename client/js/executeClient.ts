import { randomUUID } from "crypto";
import { buildPacket } from "./packetBuilder";
import { ExecuteOptions, SignatureAlgorithm, TenantContext } from "./types";

export class ExecuteClient {
  constructor(private baseUrl: string, private retries = 2, private signingKey: string | null = null, private signingAlgorithm: SignatureAlgorithm = "hmac-sha256", private signingKeyId = "client-key") {}

  async execute(action: string, payload: Record<string, unknown>, tenant: TenantContext, options: ExecuteOptions) {
    const opts = this.retries > 0 && !options.idempotencyKey ? { ...options, idempotencyKey: `auto-${randomUUID()}` } : options;
    const packet = buildPacket(action, payload, tenant, opts, this.signingKey, this.signingAlgorithm, this.signingKeyId);
    let lastErr: unknown;
    for (let i = 0; i <= this.retries; i += 1) {
      try {
        const resp = await fetch(`${this.baseUrl}/v1/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(packet) });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
      } catch (err) {
        lastErr = err;
        if (i < this.retries) await new Promise(r => setTimeout(r, 500 * (2 ** i)));
      }
    }
    throw lastErr;
  }
}
