from __future__ import annotations

from chassis.types import PacketEnvelope

ALLOWED_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}


class ClassificationError(Exception):
    pass


def enforce_classification(packet: PacketEnvelope, min_level: str = "internal") -> None:
    levels = ["public", "internal", "confidential", "restricted"]
    if min_level not in levels:
        raise ClassificationError(f"Unknown min_level: {min_level!r}")
    if packet.security is None:
        raise ClassificationError("security section absent")
    actual = packet.security.classification
    if actual not in ALLOWED_CLASSIFICATIONS:
        raise ClassificationError(f"Unknown classification '{actual}'")
    if levels.index(actual) < levels.index(min_level):
        raise ClassificationError(
            f"Packet classification '{actual}' is below required '{min_level}'"
        )
