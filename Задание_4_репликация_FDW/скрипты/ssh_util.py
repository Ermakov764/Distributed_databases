#!/usr/bin/env python3
"""SSH helper for lab 4 on both VMs."""

from __future__ import annotations

import base64
import shlex
import textwrap

import paramiko

VM1 = "192.168.122.59"
VM2 = "192.168.122.60"
USER = "db1"
PASSWORD = "1"


def connect(host: str) -> paramiko.SSHClient:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        host,
        username=USER,
        password=PASSWORD,
        timeout=25,
        allow_agent=False,
        look_for_keys=False,
    )
    return c


def run(c: paramiko.SSHClient, cmd: str, timeout: int = 300) -> tuple[int, str, str]:
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def sudo_script(c: paramiko.SSHClient, script: str, timeout: int = 300) -> tuple[int, str, str]:
    """Upload script and run with sudo -S."""
    script = textwrap.dedent(script).strip() + "\n"
    b64 = base64.b64encode(script.encode()).decode()
    remote = f"/tmp/lab4_{abs(hash(script)) % 10_000_000}.sh"
    cmd = (
        f"echo {b64} | base64 -d > {remote} && chmod +x {remote} && "
        f"echo {shlex.quote(PASSWORD)} | sudo -S -p '' bash {remote}; "
        f"ec=$?; rm -f {remote}; exit $ec"
    )
    return run(c, cmd, timeout=timeout)


def sudo_ok(c: paramiko.SSHClient, script: str, **kw) -> str:
    code, out, err = sudo_script(c, script, **kw)
    if code != 0:
        raise RuntimeError(f"sudo script failed ({code})\nOUT:\n{out}\nERR:\n{err}")
    return out
