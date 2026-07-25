from __future__ import annotations

import asyncio

from .database import create_schema
from .pipeline import worker_loop


def main() -> None:
    create_schema()
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
