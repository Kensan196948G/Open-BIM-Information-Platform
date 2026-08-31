"""Minimal clamd (ClamAV) client — no third-party dependency.

Implements the clamd INSTREAM protocol over TCP using asyncio streams:
  - PING -> PONG
  - zINSTREAM\\0 [size(4B BE) chunk]* [0-size] -> "stream: OK\\0" / "stream: <sig> FOUND\\0"
"""

import asyncio
import struct
from dataclasses import dataclass

from app.core.config import settings

CHUNK_SIZE = 64 * 1024


@dataclass
class ScanResult:
    clean: bool
    reason: str


async def _read_response(reader: asyncio.StreamReader) -> str:
    data = bytearray()
    while True:
        chunk = await reader.read(1024)
        if not chunk:
            break
        data.extend(chunk)
        if b"\0" in chunk:
            break
    return data.split(b"\0", 1)[0].decode("utf-8", errors="replace").strip()


async def ping_clamd(timeout_seconds: float = 3) -> None:
    """Raise when clamd is unavailable or returns an invalid PING response."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(settings.CLAMD_HOST, settings.CLAMD_PORT),
        timeout=min(timeout_seconds, settings.CLAMD_TIMEOUT_SECONDS),
    )
    try:
        writer.write(b"PING\n")
        await writer.drain()
        ping = await asyncio.wait_for(
            _read_response(reader),
            timeout=min(timeout_seconds, settings.CLAMD_TIMEOUT_SECONDS),
        )
        if ping != "PONG":
            raise OSError(f"clamd PING failed: {ping!r}")
    finally:
        writer.close()
        await writer.wait_closed()


async def scan_bytes(data: bytes) -> ScanResult:
    """Scan in-memory bytes via clamd. Raises OSError when clamd is unavailable."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(settings.CLAMD_HOST, settings.CLAMD_PORT),
        timeout=settings.CLAMD_TIMEOUT_SECONDS,
    )
    try:
        writer.write(b"PING\n")
        await writer.drain()
        ping = await _read_response(reader)
        if ping != "PONG":
            raise OSError(f"clamd PING failed: {ping!r}")

        writer.write(b"zINSTREAM\0")
        for i in range(0, len(data), CHUNK_SIZE):
            chunk = data[i : i + CHUNK_SIZE]
            writer.write(struct.pack(">I", len(chunk)) + chunk)
        writer.write(struct.pack(">I", 0))
        await writer.drain()

        response = await _read_response(reader)
        if "FOUND" in response:
            return ScanResult(clean=False, reason=response)
        if "OK" not in response:
            raise OSError(f"clamd scan returned unexpected response: {response!r}")
        return ScanResult(clean=True, reason=response)
    finally:
        writer.close()
        await writer.wait_closed()
