#!/usr/bin/env python3
"""Часть 1: снимки libvirt + PostgreSQL streaming replication."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ssh_util import VM1, VM2, connect, sudo_ok, sudo_script

PGDATA = "/var/lib/postgresql/16/main"
PGCONF_D = "/etc/postgresql/16/main"


def virsh_snapshot(domain: str, name: str, desc: str) -> None:
    subprocess.run(
        ["virsh", "--connect", "qemu:///system", "snapshot-delete", domain, name],
        capture_output=True,
    )
    for args in (
        ["--atomic"],
        ["--disk-only", "--atomic"],
    ):
        r = subprocess.run(
            [
                "virsh", "--connect", "qemu:///system", "snapshot-create-as",
                domain, name, "--description", desc, *args,
            ],
            capture_output=True,
            text=True,
        )
        print(domain, args, r.stdout.strip() or r.stderr.strip())
        if r.returncode == 0:
            return
    raise RuntimeError(f"snapshot failed for {domain}")


def configure_primary(c) -> None:
    print("=== Primary", VM1, "===")
    sudo_ok(
        c,
        f"""
        set -e
        cat > {PGCONF_D}/conf.d/99-replication.conf <<'EOF'
listen_addresses = '*'
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
hot_standby = on
wal_keep_size = 256MB
EOF
        HBA={PGCONF_D}/pg_hba.conf
        if ! grep -q 'lab4 replication' "$HBA"; then
          cat >> "$HBA" <<'EOF'

# lab4 replication / app
host    replication     replicator      192.168.122.0/24    scram-sha-256
host    all             all             192.168.122.0/24    scram-sha-256
EOF
        fi
        sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'replicator') THEN
    CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '1';
  ELSE
    ALTER ROLE replicator WITH REPLICATION LOGIN PASSWORD '1';
  END IF;
END$$;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'slot_lab4') THEN
    PERFORM pg_create_physical_replication_slot('slot_lab4');
  END IF;
END$$;
SQL
        systemctl restart postgresql
        sleep 2
        systemctl is-active postgresql
        sudo -u postgres psql -c "SHOW wal_level;"
        sudo -u postgres psql -c "SELECT slot_name, active FROM pg_replication_slots;"
        """
    )
    print("primary ready")


def main() -> None:
    print("Creating libvirt snapshots…")
    # snapshots already may exist from previous run
    for dom in ("ubuntu24.04", "ubuntu24.04-2"):
        r = subprocess.run(
            ["virsh", "--connect", "qemu:///system", "snapshot-list", dom, "--name"],
            capture_output=True,
            text=True,
        )
        if "before-lab4" not in (r.stdout or ""):
            virsh_snapshot(dom, "before-lab4", "Snapshot before lab 4 changes")
        else:
            print(dom, "snapshot before-lab4 already exists")

    c1 = connect(VM1)
    configure_primary(c1)
    c1.close()

    c2 = connect(VM2)
    code, out, err = sudo_script(
        c2,
        f"""
        set -e
        systemctl stop postgresql || true
        rm -rf {PGDATA}/*
        PGPASSWORD=1 pg_basebackup -h {VM1} -p 5432 -U replicator -D {PGDATA} -Fp -Xs -P -R -S slot_lab4
        chown -R postgres:postgres {PGDATA}
        chmod 700 {PGDATA}
        echo "hot_standby = on" > {PGCONF_D}/conf.d/99-standby.conf
        test -f {PGDATA}/standby.signal
        cat {PGDATA}/postgresql.auto.conf || true
        systemctl start postgresql
        sleep 4
        systemctl is-active postgresql
        sudo -u postgres psql -tAc "SELECT pg_is_in_recovery();"
        """,
        timeout=600,
    )
    print(out)
    print(err)
    if code != 0:
        raise RuntimeError(f"standby setup failed: {code}")
    c2.close()

    c1 = connect(VM1)
    print(sudo_ok(c1, 'sudo -u postgres psql -c "SELECT client_addr, state, sync_state FROM pg_stat_replication;"'))
    c1.close()

    import psycopg2

    for host, label in [(VM1, "primary"), (VM2, "standby")]:
        conn = psycopg2.connect(
            host=host, port=5432, dbname="university_db", user="db1_user", password="1"
        )
        cur = conn.cursor()
        cur.execute("SELECT pg_is_in_recovery(), COUNT(*) FROM students")
        print(label, cur.fetchone())
        conn.close()
    print("PART1_OK")


if __name__ == "__main__":
    main()
