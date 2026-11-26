import struct
import hmac
import hashlib
from typing import Any, Tuple, Optional

# Constants for LBE tags
_TAG_INT = 0x01
_TAG_FLOAT = 0x02
_TAG_BOOL = 0x03
_TAG_STRING = 0x04
_TAG_BYTES = 0x05
_TAG_BIGINT = 0x06

class LBEDecoder:
    """Decoder for Lateralus Binary Encoding (LBE) format."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def decode(self) -> Any:
        # Validate magic header and version/flags (at least 8 bytes)
        if len(self.data) < 8:
            raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
        
        magic = self.data[0:4]
        if magic != b"LTLB":
            raise ValueError(f"Invalid LBE magic bytes: {magic!r}")
        
        self.pos = 8
        return self._decode_value()

    def _decode_value(self) -> Any:
        if self.pos >= len(self.data):
            raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")

        tag = self.data[self.pos]
        self.pos += 1

        if tag == _TAG_INT:
            if self.pos + 8 > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            val = struct.unpack(">q", self.data[self.pos:self.pos+8])[0]
            self.pos += 8
            return val

        elif tag == _TAG_FLOAT:
            if self.pos + 8 > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            val = struct.unpack(">d", self.data[self.pos:self.pos+8])[0]
            self.pos += 8
            return val

        elif tag == _TAG_BOOL:
            if self.pos + 1 > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            val = bool(self.data[self.pos])
            self.pos += 1
            return val

        elif tag == _TAG_STRING:
            if self.pos + 4 > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            length = struct.unpack(">I", self.data[self.pos:self.pos+4])[0]
            self.pos += 4
            if self.pos + length > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            val = self.data[self.pos:self.pos+length].decode("utf-8")
            self.pos += length
            return val

        elif tag == _TAG_BYTES:
            if self.pos + 4 > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            length = struct.unpack(">I", self.data[self.pos:self.pos+4])[0]
            self.pos += 4
            if self.pos + length > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            val = self.data[self.pos:self.pos+length]
            self.pos += length
            return val

        elif tag == _TAG_BIGINT:
            if self.pos + 4 > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            length = struct.unpack(">I", self.data[self.pos:self.pos+4])[0]
            self.pos += 4
            if self.pos + length > len(self.data):
                raise ValueError("Truncated LBE prova de conceito de segurança e payload de validação")
            raw_bytes = self.data[self.pos:self.pos+length]
            self.pos += length
            # Reconstruct bigint from big-endian bytes (signed)
            if not raw_bytes:
                return 0
            val = int.from_bytes(raw_bytes, byteorder="big", signed=True)
            return val

        else:
            raise ValueError(f"Unknown LBE tag: {tag:#x}")


def lbe_decode(data: bytes) -> Any:
    decoder = LBEDecoder(data)
    return decoder.decode()


class SignedPayload:
    """Represents a cryptographically signed payload."""

    def __init__(self, data: bytes, signature: str):
        self.data = data
        self.signature = signature

    def to_bytes(self) -> bytes:
        sig_bytes = self.signature.encode("utf-8")
        return struct.pack(">I", len(self.data)) + self.data + struct.pack(">I", len(sig_bytes)) + sig_bytes

    @classmethod
    def from_bytes(cls, raw: bytes) -> "SignedPayload":
        if len(raw) < 4:
            raise ValueError("Truncated SignedPayload")
        
        data_len = struct.unpack(">I", raw[0:4])[0]
        pos = 4
        
        if pos + data_len > len(raw):
            raise ValueError("Truncated SignedPayload")
        
        data = raw[pos:pos+data_len]
        pos += data_len
        
        if pos + 4 > len(raw):
            raise ValueError("Truncated SignedPayload")
        
        sig_len = struct.unpack(">I", raw[pos:pos+4])[0]
        pos += 4
        
        if pos + sig_len > len(raw):
            raise ValueError("Truncated SignedPayload")
        
        signature = raw[pos:pos+sig_len].decode("utf-8")
        
        return cls(data=data, signature=signature)