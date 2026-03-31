from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx

from client.packet_builder import PacketBuilder
from client.response_parser import ResponseParser
from client.request_models import ExecuteOptions


class ExecuteClient:
    def __init__(self, *, base_url: str, retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self.builder = PacketBuilder()
        self.parser = ResponseParser()

    async def execute(self, *, action: str, payload: dict, tenant, options: ExecuteOptions) -> dict:
        if self.retries > 0 and not options.idempotency_key:
            options = options.model_copy(update={"idempotency_key": f"auto-{uuid4()}"})
        packet = self.builder.build(action=action, payload=payload, tenant=tenant, destination_node=options.destination_node, source_node=options.source_node, reply_to=options.reply_to or options.source_node)
        async with httpx.AsyncClient() as client:
            last = None
            for i in range(self.retries + 1):
                try:
                    resp = await client.post(f"{self.base_url}/v1/execute", json=packet.dict(), timeout=options.timeout_ms / 1000)
                    resp.raise_for_status()
                    return self.parser.parse(resp.json())
                except httpx.TimeoutException as exc:
                    last = exc
                except httpx.HTTPStatusError:
                    raise
                except httpx.TransportError as exc:
                    last = exc
                if i < self.retries:
                    await asyncio.sleep(0.5 * (2 ** i))
            raise RuntimeError("request failed") from last
