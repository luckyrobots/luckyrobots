"""
Shared memory header definition matching the C# ShmHeader struct.

The header is at offset 0 of the memory-mapped file and is 4096 bytes
(padded for cache-line alignment). All fields must match the C# layout
in Hazel.Net.Ipc.ShmHeader exactly.
"""

import ctypes

MAGIC_VALUE = 0x4C524243  # "LRBC" (LuckyRobots Binary Channel)
CURRENT_VERSION = 1
HEADER_SIZE = 4096


class ShmHeader(ctypes.Structure):
    """Mirrors Hazel.Net.Ipc.ShmHeader with explicit field offsets.

    The C# struct uses [FieldOffset] for explicit layout. ctypes.Structure
    lays fields sequentially, so we include Reserved0 to maintain alignment.
    """

    _fields_ = [
        # Identity (offset 0)
        ("magic", ctypes.c_uint32),          # 0
        ("version", ctypes.c_uint32),        # 4
        ("engine_pid", ctypes.c_uint32),     # 8
        ("client_pid", ctypes.c_uint32),     # 12
        # Sizing (offset 16)
        ("num_envs", ctypes.c_uint32),       # 16
        ("obs_size", ctypes.c_uint32),       # 20
        ("act_size", ctypes.c_uint32),       # 24
        ("reserved0", ctypes.c_uint32),      # 28
        # Atomic sequence counters (offset 32)
        ("frame_seq", ctypes.c_int64),       # 32
        ("action_seq", ctypes.c_int64),      # 40
        # Region offsets (offset 48)
        ("obs_offset", ctypes.c_uint64),     # 48
        ("act_offset", ctypes.c_uint64),     # 56
        ("reward_offset", ctypes.c_uint64),  # 64
        ("done_offset", ctypes.c_uint64),    # 72
        ("reset_offset", ctypes.c_uint64),   # 80
        ("schema_offset", ctypes.c_uint64),  # 88
        ("cmd_in_offset", ctypes.c_uint64),  # 96
        ("cmd_out_offset", ctypes.c_uint64), # 104
        # Total file size (offset 112)
        ("total_size", ctypes.c_uint64),     # 112
        # Status flags (offset 120)
        ("engine_ready", ctypes.c_uint32),   # 120
        ("client_ready", ctypes.c_uint32),   # 124
    ]

    def validate(self) -> None:
        """Validate the header magic number and version.

        Raises:
            ValueError: If magic or version don't match.
        """
        if self.magic != MAGIC_VALUE:
            raise ValueError(
                f"Invalid shared memory magic: 0x{self.magic:08X} "
                f"(expected 0x{MAGIC_VALUE:08X}). "
                f"Is this a LuckyEngine shared memory region?"
            )
        if self.version != CURRENT_VERSION:
            raise ValueError(
                f"Unsupported shared memory version: {self.version} "
                f"(expected {CURRENT_VERSION}). "
                f"Engine and client versions may be mismatched."
            )
