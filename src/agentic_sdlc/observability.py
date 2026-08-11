"""Tracing for the flow.

Turning this on makes each agent run, each tool call, and each approval decision
appear as spans in Application Insights. The approval decisions arrive as span
events from `TraceSink`, so the trace shows the human step inline with the model
steps rather than in a separate system.

Optional in the live session: it needs an Application Insights resource
connected to the Foundry project.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def enable_tracing(client, enable_sensitive_data: bool = True) -> bool:
    """Wire the Foundry client up to Azure Monitor. Returns whether it worked.

    `enable_sensitive_data` includes prompts and responses in the trace, which is
    what makes a trace useful for debugging an agent and unacceptable in
    production against real customer data. It is on here because the corpus and
    the initiatives are fictional.
    """
    try:
        client.configure_azure_monitor(enable_sensitive_data=enable_sensitive_data)
    except ImportError:
        logger.warning(
            "Tracing needs the Azure Monitor exporter. Install it with: "
            "pip install azure-monitor-opentelemetry"
        )
        return False
    except Exception as exc:  # noqa: BLE001 - tracing must never break a run
        logger.warning(
            "Could not enable tracing (%s). Connect an Application Insights "
            "resource to the Foundry project, or set ENABLE_TRACING=false.",
            exc,
        )
        return False

    logger.info("Tracing enabled; spans are going to Application Insights.")
    return True
