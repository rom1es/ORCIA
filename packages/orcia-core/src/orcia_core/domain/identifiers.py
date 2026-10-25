"""UUIDv7 identifier generator and validator (RFC 9562).

All database primary keys and domain entity identifiers in ORCIA use monotonic UUIDv7.
"""

from __future__ import annotations

import uuid

import uuid_utils


def new_uuid7() -> uuid.UUID:
    """Generate a new RFC 9562 monotonic UUIDv7 as a standard Python `uuid.UUID`."""
    raw = uuid_utils.uuid7()
    return uuid.UUID(bytes=raw.bytes)


def new_uuid7_str() -> str:
    """Generate a new RFC 9562 monotonic UUIDv7 formatted as a canonical lowercase string."""
    return str(new_uuid7())


def is_valid_uuid7(value: uuid.UUID | str) -> bool:
    """Return True if and only if `value` is a valid RFC 9562 UUIDv7 (version 7, RFC variant)."""
    try:
        parsed = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return False
    return parsed.version == 7 and parsed.variant == uuid.RFC_4122


def extract_uuid7_timestamp_ms(value: uuid.UUID | str) -> int:
    """Extract the 48-bit Unix epoch millisecond timestamp embedded in a UUIDv7."""
    parsed = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    if not is_valid_uuid7(parsed):
        raise ValueError(f"Expected a valid UUIDv7, got {value!r}")
    return parsed.int >> 80
