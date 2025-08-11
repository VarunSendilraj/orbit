"""
LLM-powered planner using OpenAI or Anthropic for function calling.
Provides intelligent natural language command parsing with tool selection.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, List, Optional, Literal

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional

from .schemas import (
    get_openai_function_definitions,
    get_anthropic_tool_definitions,
    validate_tool_args,
)

logger = logging.getLogger(__name__)


class LLMPlanner:
    """LLM-powered planner with support for OpenAI and Anthropic."""

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = provider
        self.api_key = api_key or self._get_api_key()
        self.model = model or self._get_default_model()
        self.client = self._create_client()

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        if self.provider == "openai":
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            return key
        elif self.provider == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            return key
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _get_default_model(self) -> str:
        """Get default model for the provider."""
        if self.provider == "openai":
            return "gpt-4o-mini"
        elif self.provider == "anthropic":
            return "claude-3-5-sonnet-20241022"
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _create_client(self):
        """Create the appropriate client for the provider."""
        if self.provider == "openai":
            try:
                import openai

                return openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        elif self.provider == "anthropic":
            try:
                import anthropic

                return anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def plan(self, command: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Plan a natural language command using LLM function calling.

        Args:
            command: Natural language command
            context: Optional context about current state

        Returns:
            List of tool calls with 'tool' and 'args' keys
        """
        try:
            if self.provider == "openai":
                return await self._plan_openai(command, context)
            elif self.provider == "anthropic":
                return await self._plan_anthropic(command, context)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
        except Exception as e:
            logger.error(f"LLM planning failed: {e}")
            return []

    async def _plan_openai(
        self, command: str, context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Plan using OpenAI function calling."""
        system_prompt = self._get_system_prompt(context)
        functions = get_openai_function_definitions()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": command},
                ],
                tools=functions,
                tool_choice="auto",
            )

            message = response.choices[0].message

            if not message.tool_calls:
                logger.warning(f"No tool calls generated for command: {command}")
                return []

            steps = []
            for tool_call in message.tool_calls:
                try:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # Validate arguments against schema
                    validated_args = validate_tool_args(function_name, function_args)

                    steps.append({"tool": function_name, "args": validated_args})
                except Exception as e:
                    logger.error(f"Error processing tool call {tool_call}: {e}")
                    continue

            return steps

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return []

    async def _plan_anthropic(
        self, command: str, context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Plan using Anthropic Claude function calling."""
        system_prompt = self._get_system_prompt(context)
        tools = get_anthropic_tool_definitions()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": command}],
                tools=tools,
            )

            steps = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    try:
                        function_name = content_block.name
                        function_args = content_block.input

                        # Validate arguments against schema
                        validated_args = validate_tool_args(function_name, function_args)

                        steps.append({"tool": function_name, "args": validated_args})
                    except Exception as e:
                        logger.error(f"Error processing tool use {content_block}: {e}")
                        continue

            if not steps:
                logger.warning(f"No tool calls generated for command: {command}")

            return steps

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return []

    def _get_system_prompt(self, context: Optional[str] = None) -> str:
        """Get the system prompt for the LLM."""
        base_prompt = """You are Orbit, a macOS AI assistant that helps users automate tasks across their system and apps.

Your job is to:
1. Parse natural language commands into executable tool calls
2. Choose the appropriate tools for each task
3. Break down complex requests into sequential steps
4. Provide arguments that will successfully complete the user's intent

Available capabilities:
- Browser automation (navigate, click, type, screenshot, get text)
- File system operations (read, write, list, create directories, move, delete, reveal in Finder)  
- Calendar management (create events, list upcoming events, delete events)
- Spotify control (play, pause, next/previous track, get current song, search)
- App launching and basic macOS interactions

Guidelines:
- For multi-step tasks, break them into logical sequential steps
- Use specific CSS selectors for web automation (prefer IDs and classes)
- Use full file paths when possible, ~ for home directory is supported
- For calendar events, parse dates naturally (e.g., "today at 3pm", "next Friday")
- Be conservative with destructive operations (file deletion)
- If a command is ambiguous, choose the most likely interpretation

Call the appropriate functions to complete the user's request."""

        if context:
            return f"{base_prompt}\n\nCurrent context:\n{context}"

        return base_prompt


# Global LLM planner instance
_llm_planner: Optional[LLMPlanner] = None


def get_llm_planner() -> Optional[LLMPlanner]:
    """Get the global LLM planner instance."""
    global _llm_planner

    if _llm_planner is None:
        try:
            # Try to initialize with environment variables
            if os.environ.get("OPENAI_API_KEY"):
                _llm_planner = LLMPlanner(provider="openai")
            elif os.environ.get("ANTHROPIC_API_KEY"):
                _llm_planner = LLMPlanner(provider="anthropic")
            else:
                logger.warning("No LLM API keys found in environment. LLM planning disabled.")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize LLM planner: {e}")
            return None

    return _llm_planner


def configure_llm_planner(
    provider: Literal["openai", "anthropic"], api_key: str, model: Optional[str] = None
) -> None:
    """Configure the global LLM planner."""
    global _llm_planner
    _llm_planner = LLMPlanner(provider=provider, api_key=api_key, model=model)


async def plan_with_llm(command: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Plan a command using LLM if available, otherwise return empty list.

    Args:
        command: Natural language command
        context: Optional context about current state

    Returns:
        List of tool calls or empty list if LLM planning fails
    """
    planner = get_llm_planner()
    if not planner:
        return []

    return await planner.plan(command, context)
