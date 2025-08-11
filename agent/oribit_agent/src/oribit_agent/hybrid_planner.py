"""
Hybrid planner that combines LLM-powered planning with deterministic fallback.
Tries LLM first for intelligent parsing, falls back to regex-based planner for reliability.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from .llm_planner import plan_with_llm
from .planner import plan as deterministic_plan

logger = logging.getLogger(__name__)


class HybridPlanner:
    """Hybrid planner with LLM-first, deterministic-fallback strategy."""

    def __init__(self, enable_llm: bool = True, fallback_always: bool = False):
        """
        Initialize hybrid planner.

        Args:
            enable_llm: Whether to attempt LLM planning
            fallback_always: If True, always try deterministic planner even if LLM succeeds
        """
        self.enable_llm = enable_llm
        self.fallback_always = fallback_always

    async def plan(
        self, command: str, context: Optional[str] = None, prefer_deterministic: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Plan a natural language command using hybrid approach.

        Args:
            command: Natural language command
            context: Optional context about current state
            prefer_deterministic: If True, try deterministic planner first

        Returns:
            List of tool calls with 'tool' and 'args' keys
        """
        steps: List[Dict[str, Any]] = []
        llm_attempted = False
        llm_succeeded = False

        # Strategy 1: Try LLM first (unless deterministic is preferred)
        if self.enable_llm and not prefer_deterministic:
            try:
                logger.debug(f"Attempting LLM planning for: {command}")
                llm_attempted = True
                steps = await plan_with_llm(command, context)

                if steps:
                    llm_succeeded = True
                    logger.info(f"LLM planning succeeded with {len(steps)} steps")

                    # If fallback_always is enabled, also try deterministic
                    if self.fallback_always:
                        deterministic_steps = deterministic_plan(command)
                        if deterministic_steps:
                            logger.info(
                                f"Deterministic fallback also found {len(deterministic_steps)} steps"
                            )
                            # For now, prefer LLM results but log both
                            logger.debug(f"LLM steps: {steps}")
                            logger.debug(f"Deterministic steps: {deterministic_steps}")
                else:
                    logger.warning("LLM planning returned no steps")

            except Exception as e:
                logger.error(f"LLM planning failed: {e}")

        # Strategy 2: Fallback to deterministic planner
        if not steps or prefer_deterministic:
            try:
                logger.debug(f"Attempting deterministic planning for: {command}")
                deterministic_steps = deterministic_plan(command)

                if deterministic_steps:
                    if not llm_succeeded:
                        steps = deterministic_steps
                        logger.info(f"Deterministic planning succeeded with {len(steps)} steps")
                    else:
                        logger.debug(
                            f"Deterministic planner also found {len(deterministic_steps)} steps"
                        )

                elif llm_attempted and not llm_succeeded:
                    logger.warning(f"Both LLM and deterministic planning failed for: {command}")

            except Exception as e:
                logger.error(f"Deterministic planning failed: {e}")

        # Strategy 3: Last resort - try LLM if we preferred deterministic first
        if not steps and prefer_deterministic and self.enable_llm:
            try:
                logger.debug(f"Last resort: Attempting LLM planning for: {command}")
                steps = await plan_with_llm(command, context)

                if steps:
                    logger.info(f"LLM planning (last resort) succeeded with {len(steps)} steps")

            except Exception as e:
                logger.error(f"LLM planning (last resort) failed: {e}")

        # Log final result
        if steps:
            planner_used = "hybrid"
            if llm_succeeded and not prefer_deterministic:
                planner_used = "llm"
            elif not llm_attempted or not llm_succeeded:
                planner_used = "deterministic"

            logger.info(f"Planning completed using {planner_used} strategy: {len(steps)} steps")
        else:
            logger.warning(f"All planning strategies failed for command: {command}")

        return steps


# Global hybrid planner instance
_hybrid_planner: Optional[HybridPlanner] = None


def get_hybrid_planner() -> HybridPlanner:
    """Get the global hybrid planner instance."""
    global _hybrid_planner

    if _hybrid_planner is None:
        _hybrid_planner = HybridPlanner()

    return _hybrid_planner


def configure_hybrid_planner(enable_llm: bool = True, fallback_always: bool = False) -> None:
    """Configure the global hybrid planner."""
    global _hybrid_planner
    _hybrid_planner = HybridPlanner(enable_llm=enable_llm, fallback_always=fallback_always)


async def hybrid_plan(
    command: str, context: Optional[str] = None, prefer_deterministic: bool = False
) -> List[Dict[str, Any]]:
    """
    Plan a command using the hybrid approach.

    Args:
        command: Natural language command
        context: Optional context about current state
        prefer_deterministic: If True, try deterministic planner first

    Returns:
        List of tool calls
    """
    planner = get_hybrid_planner()
    return await planner.plan(command, context, prefer_deterministic)


def analyze_command_complexity(command: str) -> Dict[str, Any]:
    """
    Analyze command complexity to help decide planning strategy.

    Args:
        command: Natural language command

    Returns:
        Dictionary with complexity analysis
    """
    cmd_lower = command.lower().strip()

    # Simple heuristics for complexity analysis
    analysis = {
        "word_count": len(cmd_lower.split()),
        "has_conjunctions": any(word in cmd_lower for word in ["and", "then", "after", "before"]),
        "has_conditionals": any(word in cmd_lower for word in ["if", "when", "unless", "while"]),
        "has_ambiguous_refs": any(
            word in cmd_lower for word in ["this", "that", "it", "the previous"]
        ),
        "has_temporal_refs": any(
            word in cmd_lower for word in ["today", "tomorrow", "next", "last", "in"]
        ),
        "has_complex_selectors": any(
            word in cmd_lower for word in ["containing", "with", "like", "similar"]
        ),
        "simple_patterns": [],
        "complexity_score": 0,
    }

    # Check for simple deterministic patterns
    simple_patterns = [
        ("create file", "create" in cmd_lower and "file" in cmd_lower),
        (
            "open app",
            "open" in cmd_lower
            and any(app in cmd_lower for app in ["app", "safari", "chrome", "notion"]),
        ),
        (
            "navigate url",
            any(word in cmd_lower for word in ["navigate", "go to"])
            and any(word in cmd_lower for word in ["http", "www", ".com", ".org"]),
        ),
        (
            "play music",
            any(word in cmd_lower for word in ["play", "pause", "next", "previous"])
            and any(word in cmd_lower for word in ["music", "spotify"]),
        ),
        ("list files", "list" in cmd_lower and ("file" in cmd_lower or "director" in cmd_lower)),
    ]

    for pattern_name, matches in simple_patterns:
        if matches:
            analysis["simple_patterns"].append(pattern_name)

    # Calculate complexity score (0-10, higher = more complex)
    score = 0
    score += min(analysis["word_count"] // 3, 3)  # Word count contribution (0-3)
    score += 2 if analysis["has_conjunctions"] else 0
    score += 2 if analysis["has_conditionals"] else 0
    score += 1 if analysis["has_ambiguous_refs"] else 0
    score += 1 if analysis["has_temporal_refs"] else 0
    score += 2 if analysis["has_complex_selectors"] else 0
    score -= len(analysis["simple_patterns"])  # Simple patterns reduce complexity

    analysis["complexity_score"] = max(0, min(10, score))

    # Suggest planning strategy
    if analysis["complexity_score"] <= 2 and analysis["simple_patterns"]:
        analysis["suggested_strategy"] = "deterministic_first"
    elif analysis["complexity_score"] >= 7:
        analysis["suggested_strategy"] = "llm_first"
    else:
        analysis["suggested_strategy"] = "hybrid"

    return analysis


async def smart_plan(command: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Smart planning that uses complexity analysis to choose the best strategy.

    Args:
        command: Natural language command
        context: Optional context about current state

    Returns:
        List of tool calls
    """
    analysis = analyze_command_complexity(command)

    logger.debug(f"Command analysis: {analysis}")

    prefer_deterministic = analysis["suggested_strategy"] == "deterministic_first"

    return await hybrid_plan(command, context, prefer_deterministic)
