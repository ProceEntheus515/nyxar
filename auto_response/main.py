"""Punto de entrada del servicio auto_response (Change Stream / polling sobre incidents)."""

from __future__ import annotations

import asyncio

from auto_response.engine import ResponseEngine


async def _main() -> None:
    await ResponseEngine().start()


if __name__ == "__main__":
    asyncio.run(_main())
