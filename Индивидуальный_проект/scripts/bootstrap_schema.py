#!/usr/bin/env python3
"""Применяет схему и seed на primary WEST/EAST (после docker compose up)."""

from __future__ import annotations

import time
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "db/init/01_schema.sql"
SEED = {
    "WEST": ROOT / "db/init/west/02_seed.sql",
    "EAST": ROOT / "db/init/east/02_seed.sql",
}
DSN = {
    "WEST": "postgresql://warehouse:warehouse@127.0.0.1:15432/warehouse",
    "EAST": "postgresql://warehouse:warehouse@127.0.0.1:15434/warehouse",
}


def run_sql_file(conn: psycopg.Connection, path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # Простые DDL/DML без процедур — достаточно split по ';'
    statements = [s.strip() for s in text.split(";") if s.strip() and not s.strip().startswith("--")]
    with conn.cursor() as cur:
        for stmt in statements:
            # пропуск чисто комментариевых блоков
            lines = [ln for ln in stmt.splitlines() if ln.strip() and not ln.strip().startswith("--")]
            if not lines:
                continue
            cur.execute("\n".join(lines))


def wait_and_apply(region: str, dsn: str, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with psycopg.connect(dsn, connect_timeout=3) as conn:
                run_sql_file(conn, SCHEMA)
                run_sql_file(conn, SEED[region])
                conn.commit()
            print(f"OK {region}: schema+seed applied via {dsn.split('@')[1]}")
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"retry {region}: {exc}")
            time.sleep(2)
    raise SystemExit(f"FAIL {region}: {last_err}")


def main() -> None:
    for region, dsn in DSN.items():
        wait_and_apply(region, dsn)


if __name__ == "__main__":
    main()
