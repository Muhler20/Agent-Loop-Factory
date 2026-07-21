from __future__ import annotations

import fnmatch
import re
from typing import Sequence


_PATTERNS = (
    "src/agent_loop_factory/verifier.py",
    "src/agent_loop_factory/run_gates.py",
    "src/agent_loop_factory/config.py",
    "src/agent_loop_factory/orchestrator.py",
    "src/agent_loop_factory/codex_implementer.py",
    "src/agent_loop_factory/advisory_reviewer.py",
    "src/agent_loop_factory/planning_agents.py",
    "src/agent_loop_factory/memory_context.py",
    "src/agent_loop_factory/memory_proposal.py",
    "src/agent_loop_factory/memory_registry.py",
    "src/agent_loop_factory/github_context.py",
    "src/agent_loop_factory/report_config.py",
    "src/agent_loop_factory/scheduled_report.py",
    "src/agent_loop_factory/report_trigger_handoff.py",
    "scripts/run_agent_loop.py",
    "scripts/run_agent_planning.py",
    ".agent/config.yaml",
    ".github/workflows/*",
    "reviewers/*",
    "memory/INDEX.md",
    "memory/*",
)
_PATHS = re.compile(r"(?<![\w./-])\.?[\w.-]+(?:/[\w.*-]+)+(?![\w./-])")


def safety_core_patterns() -> tuple[str, ...]:
    return _PATTERNS


def find_safety_core_references(text: str, context_paths: Sequence[str] = ()) -> dict[str, object]:
    candidates = [path.rstrip(".,:;") for path in _PATHS.findall(text)] + [path.replace("\\", "/").removeprefix("./") for path in context_paths]
    matches = tuple(dict.fromkeys(
        candidate
        for candidate in candidates
        if any(fnmatch.fnmatchcase(candidate, pattern) for pattern in _PATTERNS)
    ))
    matched_patterns = tuple(pattern for pattern in _PATTERNS if any(fnmatch.fnmatchcase(match, pattern) for match in matches))
    return {"references_detected": bool(matches), "matches": matches, "matched_paths": matches, "matched_patterns": matched_patterns}
