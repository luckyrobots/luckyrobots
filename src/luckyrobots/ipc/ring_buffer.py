"""
SPSC ring buffer reader/writer for IPC command channel.

Matches the layout in SpscRingBuffer.cs:
  [0..7]     head     (uint64, producer writes)
  [8..63]    padding
  [64..71]   tail     (uint64, consumer writes)
  [72..127]  padding
  [128..131] capacity (uint32)
  [132..191] padding
  [192..]    data area

Envelope per message (16 bytes + payload):
  [0..3]   correlation_id  (uint32)
  [4..7]   method_id       (uint32)
  [8..11]  payload_length  (uint32)
  [12..15] reserved        (uint32)
  [16..]   payload bytes
"""

from __future__ import annotations

import ctypes
import struct
import time
from typing import Optional


RING_HEADER_SIZE = 192
ENVELOPE_HEADER_SIZE = 16
ENVELOPE_FMT = "<III4x"  # corr_id, method_id, payload_len, 4 bytes reserved


class SpscRingWriter:
    """Write messages to a SPSC ring buffer (producer side)."""

    def __init__(self, mm: memoryview, offset: int, size: int) -> None:
        self._mm = mm
        self._base = offset
        self._head_off = offset  # head at byte 0
        self._tail_off = offset + 64  # tail at byte 64
        self._cap_off = offset + 128  # capacity at byte 128
        self._data_off = offset + RING_HEADER_SIZE

        # Read capacity (set by engine during init)
        self._capacity = struct.unpack_from("<I", mm, self._cap_off)[0]
        if self._capacity == 0:
            # Fallback: compute from region size
            self._capacity = _next_pow2(size - RING_HEADER_SIZE)
            if self._capacity > size - RING_HEADER_SIZE:
                self._capacity >>= 1
        self._mask = self._capacity - 1

    def write(self, correlation_id: int, method_id: int, payload: bytes) -> bool:
        """Write a command message. Returns False if buffer is full."""
        msg_size = _align8(ENVELOPE_HEADER_SIZE + len(payload))

        head = struct.unpack_from("<Q", self._mm, self._head_off)[0]
        tail = struct.unpack_from("<Q", self._mm, self._tail_off)[0]
        used = head - tail

        if used + msg_size > self._capacity:
            return False

        # Write envelope header
        hdr = struct.pack("<III4x", correlation_id, method_id, len(payload))
        self._write_wrapping(head, hdr)

        # Write payload
        if payload:
            self._write_wrapping(head + ENVELOPE_HEADER_SIZE, payload)

        # Advance head (release)
        struct.pack_into("<Q", self._mm, self._head_off, head + msg_size)
        return True

    def _write_wrapping(self, pos: int, data: bytes) -> None:
        offset = int(pos & self._mask)
        first = min(len(data), self._capacity - offset)
        abs_off = self._data_off + offset
        self._mm[abs_off: abs_off + first] = data[:first]
        if first < len(data):
            self._mm[self._data_off: self._data_off + len(data) - first] = data[first:]


class SpscRingReader:
    """Read messages from a SPSC ring buffer (consumer side)."""

    def __init__(self, mm: memoryview, offset: int, size: int) -> None:
        self._mm = mm
        self._base = offset
        self._head_off = offset
        self._tail_off = offset + 64
        self._cap_off = offset + 128
        self._data_off = offset + RING_HEADER_SIZE

        self._capacity = struct.unpack_from("<I", mm, self._cap_off)[0]
        if self._capacity == 0:
            self._capacity = _next_pow2(size - RING_HEADER_SIZE)
            if self._capacity > size - RING_HEADER_SIZE:
                self._capacity >>= 1
        self._mask = self._capacity - 1

    def read(self) -> Optional[tuple[int, int, bytes]]:
        """Try to read a message. Returns (corr_id, method_id/status, payload) or None."""
        head = struct.unpack_from("<Q", self._mm, self._head_off)[0]
        tail = struct.unpack_from("<Q", self._mm, self._tail_off)[0]

        if head == tail:
            return None

        # Read envelope
        hdr = self._read_wrapping(tail, ENVELOPE_HEADER_SIZE)
        corr_id, method_or_status, payload_len = struct.unpack_from("<III", hdr, 0)

        # Read payload
        payload = b""
        if payload_len > 0:
            payload = self._read_wrapping(tail + ENVELOPE_HEADER_SIZE, payload_len)

        # Advance tail
        msg_size = _align8(ENVELOPE_HEADER_SIZE + payload_len)
        struct.pack_into("<Q", self._mm, self._tail_off, tail + msg_size)

        return (corr_id, method_or_status, payload)

    def has_pending(self) -> bool:
        head = struct.unpack_from("<Q", self._mm, self._head_off)[0]
        tail = struct.unpack_from("<Q", self._mm, self._tail_off)[0]
        return head != tail

    def _read_wrapping(self, pos: int, length: int) -> bytes:
        offset = int(pos & self._mask)
        first = min(length, self._capacity - offset)
        abs_off = self._data_off + offset
        result = bytes(self._mm[abs_off: abs_off + first])
        if first < length:
            result += bytes(self._mm[self._data_off: self._data_off + length - first])
        return result


def _align8(v: int) -> int:
    return (v + 7) & ~7


def _next_pow2(v: int) -> int:
    v -= 1
    v |= v >> 1
    v |= v >> 2
    v |= v >> 4
    v |= v >> 8
    v |= v >> 16
    v += 1
    return v
