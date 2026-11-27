"""
Encoding standard library module for Lateralus.
Provides base64, hex, and LBE (Lateralus Binary Encoding) codecs.
"""

import struct

def lbe_decode(data: bytes) -> str:
    """
    Decodes LBE (Lateralus Binary Encoding) format into a UTF-8 string.
    Strictly validates that the length prefix matches the actual remaining data
    and that no trailing bytes are present.
    """
    if not isinstance(data, bytes):
        raise TypeError("lbe_decode expects bytes input")

    if len(data) < 4:
        raise ValueError("Truncated LBE payload: header too short")

    # Unpack 32-bit big-endian length prefix
    length = struct.unpack(">I", data[:4])[0]

    expected_total_len = 4 + length
    if len(data) < expected_total_len:
        raise ValueError(
            f"Truncated LBE payload: expected {expected_total_len} bytes, got {len(data)}"
        )
    if len(data) > expected_total_len:
        raise ValueError(
            f"Corrupted LBE payload: trailing bytes detected ({len(data) - expected_total_len} extra bytes)"
        )

    payload = data[4:expected_total_len]
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"Invalid UTF-8 sequence in LBE payload: {e}") from e


def lbe_encode(text: str) -> bytes:
    """
    Encodes a string into LBE format with a 32-bit big-endian length prefix.
    """
    if not isinstance(text, str):
        raise TypeError("lbe_encode expects string input")
    encoded = text.encode("utf-8")
    length = len(encoded)
    return struct.pack(">I", length) + encoded