import { createHash, createHmac, createPrivateKey, randomUUID, sign as cryptoSign } from "crypto";
import { ExecuteOptions, SignatureAlgorithm, TenantContext } from "./types";

function sha256Hex(v: unknown): string { return createHash("sha256").update(JSON.stringify(v)).digest("hex"); }
function decodeKey(key: string): Buffer { try { return Buffer.from(key, "base64"); } catch { return Buffer.from(key, "utf8"); } }

export function buildPacket(action: string, payload: Record<string, unknown>, tenant: TenantContext, options: ExecuteOptions, signingKey?: string | null, signingAlgorithm: SignatureAlgorithm = "hmac-sha256", signingKeyId = "client-key") {
  const packetId = randomUUID();
  const packet: any = {
    header: { packet_id: packetId, packet_type: "request", action, priority: 2, created_at: new Date().toISOString(), timeout_ms: options.timeoutMs ?? 30000, schema_version: "1.1", trace_id: packetId, correlation_id: packetId, retry_count: 0, replay_mode: false, idempotency_key: options.idempotencyKey ?? null },
    address: { source_node: options.sourceNode ?? "client", destination_node: options.destinationNode, reply_to: options.replyTo ?? options.sourceNode ?? "client" },
    tenant,
    payload,
    security: { content_hash: sha256Hex(payload), envelope_hash: "", signature: null, signature_algorithm: null, signing_key_id: null, classification: "internal", encryption_status: "plaintext", pii_fields: [] },
    governance: { intent: action, compliance_tags: [], retention_days: 90, redaction_applied: false, audit_required: false, data_subject_id: null },
    delegation_chain: [], hop_trace: [], lineage: { parent_id: null, root_id: packetId, generation: 0 }, attachments: []
  };
  packet.security.envelope_hash = sha256Hex({ header: packet.header, address: packet.address, tenant: packet.tenant, payload: packet.payload, governance: packet.governance, delegation_chain: packet.delegation_chain, lineage: packet.lineage, attachments: packet.attachments, content_hash: packet.security.content_hash });
  if (signingKey) {
    packet.security.signature = signingAlgorithm === "ed25519"
      ? cryptoSign(null, Buffer.from(packet.security.envelope_hash, "utf8"), createPrivateKey({ key: decodeKey(signingKey), format: "pem" })).toString("hex")
      : createHmac("sha256", decodeKey(signingKey)).update(packet.security.envelope_hash, "utf8").digest("hex");
    packet.security.signature_algorithm = signingAlgorithm;
    packet.security.signing_key_id = signingKeyId;
  }
  return packet;
}
