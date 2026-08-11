"""Start all three mock systems of record in one command.

    python -m mcp_servers.run_all

Each server runs in its own process so a crash in one does not take the others
down. Ctrl+C stops all of them.
"""

from __future__ import annotations

import subprocess
import sys
import time

SERVERS = [
    ("mock Jira", "mcp_servers.mock_jira", 8931),
    ("mock GitHub", "mcp_servers.mock_github", 8932),
    ("mock Confluence", "mcp_servers.mock_confluence", 8933),
]


def main() -> int:
    processes: list[tuple[str, subprocess.Popen[bytes]]] = []
    try:
        for label, module, port in SERVERS:
            process = subprocess.Popen([sys.executable, "-m", module])
            processes.append((label, process))
            print(f"started {label} on http://127.0.0.1:{port}/mcp (pid {process.pid})")

        print("\nAll mock servers running. Press Ctrl+C to stop.")
        while True:
            for label, process in processes:
                if process.poll() is not None:
                    print(f"[!] {label} exited with code {process.returncode}")
                    return process.returncode or 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nstopping...")
        return 0
    finally:
        for _, process in processes:
            if process.poll() is None:
                process.terminate()
        for _, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
