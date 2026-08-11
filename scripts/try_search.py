"""Run one scoped hybrid search against the corpus index, outside any agent.

    python scripts/try_search.py "what happens if we are unsure whether a rule applies to us?"
    python scripts/try_search.py --doc-types architecture design_format "what are the data residency requirements?"

Defaults to the Requirements Agent's scope (dor), which lets guide 03
demonstrate both a hybrid-search hit and an honest scoped miss.
"""

from __future__ import annotations

import argparse

from agentic_sdlc.config import load_settings
from agentic_sdlc.grounding.search import build_corpus_search_tool


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the governance corpus with a scoped tool.")
    parser.add_argument("query", help="What to look for, in natural language.")
    parser.add_argument(
        "--doc-types",
        nargs="+",
        default=["dor"],
        help="Document types the tool may retrieve (default: dor).",
    )
    args = parser.parse_args()

    settings = load_settings()
    tool = build_corpus_search_tool(settings.search, settings.embedding, doc_types=args.doc_types)
    print(tool.func(args.query))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
