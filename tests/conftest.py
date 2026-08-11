"""Shared fixtures.

The mock MCP servers are started as real subprocesses rather than stubbed, so
the tests exercise the same transport the agents use.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TextIO

import pytest

from agentic_sdlc.contracts.artifacts import (
    Citation,
    DesignArtifact,
    DesignComponent,
    DesignDecision,
    DoRCheck,
    DoRChecklist,
    Requirement,
    SystemRequirements,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

MOCK_SERVERS = {
    "jira": ("mcp_servers.mock_jira", 8931),
    "github": ("mcp_servers.mock_github", 8932),
    "confluence": ("mcp_servers.mock_confluence", 8933),
}

MockProcess = tuple[subprocess.Popen[str], TextIO]


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def _wait_for_port(
    port: int,
    process: subprocess.Popen[str] | None = None,
    timeout: float = 30.0,
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open(port):
            return True
        if process is not None and process.poll() is not None:
            return False
        time.sleep(0.25)
    return False


def _stop_processes(processes: dict[str, MockProcess]) -> dict[str, str]:
    """Stop mock servers and return their combined output for diagnostics."""
    for process, _ in processes.values():
        if process.poll() is None:
            process.terminate()

    output: dict[str, str] = {}
    for name, (process, log_file) in processes.items():
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log_file.flush()
        log_file.seek(0)
        output[name] = log_file.read()
        log_file.close()
    return output


@pytest.fixture(scope="session")
def mock_servers() -> dict[str, str]:
    """Start any mock server that is not already running, and hand back URLs."""
    started: dict[str, MockProcess] = {}
    for name, (module, port) in MOCK_SERVERS.items():
        if _port_open(port):
            continue
        log_file = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        process = subprocess.Popen(
            [sys.executable, "-m", module],
            cwd=REPO_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        started[name] = (process, log_file)

    for name, (_, port) in MOCK_SERVERS.items():
        owned_process = started.get(name)
        if not _wait_for_port(port, owned_process[0] if owned_process else None):
            output = _stop_processes(started)
            diagnostics = "\n\n".join(
                f"--- {process_name} ---\n{captured or '(no output)'}"
                for process_name, captured in output.items()
            )
            pytest.fail(
                f"mock {name} did not start on port {port}. Subprocess output:\n{diagnostics}",
                pytrace=False,
            )

    yield {name: f"http://127.0.0.1:{port}/mcp" for name, (_, port) in MOCK_SERVERS.items()}

    _stop_processes(started)


@pytest.fixture
def requirements() -> SystemRequirements:
    return SystemRequirements(
        initiative_id="INIT-TEST",
        title="Test initiative",
        functional=[
            Requirement(
                id="FR-01",
                statement="The system must settle eligible claims without adjuster involvement.",
                rationale="Reduces cycle time for low-complexity claims.",
                acceptance_criteria=[
                    "Given an eligible claim, when it is assessed, then it settles without an adjuster.",
                    "Given an ineligible claim, when it is assessed, then it routes to an adjuster.",
                ],
                priority="must",
            )
        ],
        non_functional=[
            Requirement(
                id="NFR-01",
                statement="Every automated settlement decision must be reconstructable for seven years.",
                rationale="Audit obligation for automated decisions.",
                acceptance_criteria=["Given a settled claim, when audited, then inputs and rule version are retrievable."],
                priority="must",
            )
        ],
        definition_of_ready=DoRChecklist(
            checks=[
                DoRCheck(name="DoR-01", passed=True, note="Outcome stated as cycle-time reduction."),
                DoRCheck(name="DoR-06", passed=False, note="Explainability obligation unconfirmed."),
            ]
        ),
        citations=[
            Citation(
                doc_id="DOR-CHECKLIST",
                title="Definition of Ready",
                section="DoR-06 Regulatory and compliance obligations are identified",
                doc_type="dor",
            )
        ],
        open_questions=["Who confirms the explainability obligation?"],
    )


@pytest.fixture
def design() -> DesignArtifact:
    return DesignArtifact(
        initiative_id="INIT-TEST",
        overview="A rules-driven eligibility check in front of the existing settlement path.",
        components=[
            DesignComponent(
                name="Eligibility assessor",
                responsibility="Decides whether a claim may be settled automatically.",
                depends_on=["Claims intake"],
            )
        ],
        data_flows=["Claims intake sends a claim summary to the eligibility assessor on claim submission."],
        decisions=[
            DesignDecision(
                decision="Assess eligibility synchronously at intake.",
                rationale="The caller needs the routing result to proceed.",
                alternatives_considered=["Asynchronous assessment via a queue"],
            )
        ],
        risks=["Rule drift could change the automation rate without anyone noticing."],
        citations=[
            Citation(
                doc_id="ARCH-STANDARDS",
                title="Architecture Standards",
                section="ARC-05 Auditability of automated decisions",
                doc_type="architecture",
            )
        ],
    )
