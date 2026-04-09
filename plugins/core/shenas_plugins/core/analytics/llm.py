"""LLM integration for analysis modes (PR 2.3, extended for multi-mode).

This module is the bridge between the curated analytics vocabulary
(``OPERATIONS``, the catalog, the Recipe DAG) and an LLM. The LLM never
sees raw SQL, raw Ibis, or any operation that isn't in the vocabulary.
Its only job is to translate a natural-language question into a Recipe
JSON payload that the existing runner can execute.

Architecture
------------
1. :class:`LLMProvider` -- thin interface so the Anthropic implementation
   is swappable for tests (and future providers). One method:
   ``ask(system, user) -> recipe_json``.

2. :class:`AnthropicProvider` -- wraps the official ``anthropic`` SDK.
   Reads the API key from the ``ANTHROPIC_API_KEY`` env var. Sends a
   single tool-use request whose tool is a ``submit_recipe`` schema;
   the LLM must respond by calling that tool with a recipe payload.

3. :func:`build_system_prompt` -- delegates to the active
   :class:`AnalysisMode` for mode-specific framing. Falls back to a
   default prompt when no mode is supplied (backwards compatibility).

4. :func:`build_user_prompt` -- assembles the per-question payload:
   the user's question + the current catalog dump. Shared across all
   modes.

5. :func:`operation_param_schema` -- derives an Anthropic tool-use
   ``input_schema`` from an Operation dataclass's fields. Used by
   :class:`AnalysisMode` to render its operation vocabulary.

The LLM-driven mutation ``askHypothesis`` lives in
``app/graphql/mutations.py`` and uses :func:`ask_for_recipe` here.
"""

from __future__ import annotations

import dataclasses
import json
import os
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

if TYPE_CHECKING:
    from shenas_plugins.core.analytics.mode import AnalysisMode
    from shenas_plugins.core.analytics.operations import Operation

# ----------------------------------------------------------------------
# Provider interface
# ----------------------------------------------------------------------


class LLMProvider(Protocol):
    """Minimal interface every LLM provider must implement."""

    name: str
    last_input_tokens: int
    last_output_tokens: int

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Send the prompt + tools to the LLM and return the parsed tool-use payload.

        The implementation MUST instruct the model to respond by calling
        the ``submit_recipe`` tool. The return value is the dict the
        model passed as the tool's input -- caller is responsible for
        validating it against ``Recipe``. Implementations should also
        update ``last_input_tokens`` / ``last_output_tokens`` so the
        caller can record cost (PR 4.5).
        """
        ...


class FakeProvider:
    """In-process provider for tests. Returns a pre-canned recipe payload."""

    name: ClassVar[str] = "fake@v0"

    def __init__(self, payload: dict[str, Any], *, input_tokens: int = 100, output_tokens: int = 50) -> None:
        self._payload = payload
        self._in = input_tokens
        self._out = output_tokens
        self.calls: list[tuple[str, str]] = []
        self.last_input_tokens = 0
        self.last_output_tokens = 0

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]]) -> dict[str, Any]:  # noqa: ARG002
        self.calls.append((system, user))
        self.last_input_tokens = self._in
        self.last_output_tokens = self._out
        return self._payload


class AnthropicProvider:
    """Provider backed by the official Anthropic Python SDK.

    Reads the API key from ``ANTHROPIC_API_KEY``. Uses the latest
    Sonnet model by default; override via the ``model`` arg.
    """

    def __init__(self, *, model: str = "claude-sonnet-4-6", max_tokens: int = 4096) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.name = f"anthropic@{model}"
        self.last_input_tokens: int = 0
        self.last_output_tokens: int = 0

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            import anthropic
        except ImportError as exc:
            msg = "anthropic SDK not installed; pip install anthropic"
            raise RuntimeError(msg) from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "ANTHROPIC_API_KEY not set"
            raise RuntimeError(msg)

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=tools,
            tool_choice={"type": "tool", "name": "submit_recipe"},
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.last_input_tokens = int(getattr(usage, "input_tokens", 0))
            self.last_output_tokens = int(getattr(usage, "output_tokens", 0))
        # Find the tool_use block; the model is forced to call submit_recipe.
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "submit_recipe":
                return dict(block.input)
        msg = f"LLM did not call submit_recipe; got {resp.content!r}"
        raise RuntimeError(msg)


# ----------------------------------------------------------------------
# Operation -> JSON schema
# ----------------------------------------------------------------------


_PYTHON_TO_JSON_SCHEMA: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _json_type_for(annotation: Any) -> dict[str, Any]:
    """Map a dataclass field annotation to a JSON-schema type fragment."""
    import types
    import typing

    origin = typing.get_origin(annotation)
    if origin is types.UnionType or str(origin) == "typing.Union":
        non_none = [a for a in typing.get_args(annotation) if a is not type(None)]
        if non_none:
            return _json_type_for(non_none[0])
    if origin is tuple or origin is list:
        inner = typing.get_args(annotation)
        item_t = _json_type_for(inner[0]) if inner else {"type": "string"}
        return {"type": "array", "items": item_t}
    if annotation in _PYTHON_TO_JSON_SCHEMA:
        return {"type": _PYTHON_TO_JSON_SCHEMA[annotation]}
    return {"type": "string"}


def operation_param_schema(op_cls: type[Operation]) -> dict[str, Any]:
    """Derive a JSON-schema fragment for one operation's ``params`` dict.

    Walks the dataclass fields and resolves their annotations against
    the operation module's globals so ``from __future__ import annotations``
    string-form types become real Python types.
    """
    import typing

    hints = typing.get_type_hints(op_cls, include_extras=True)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for f in dataclasses.fields(op_cls):
        annotation = hints.get(f.name, str)
        properties[f.name] = _json_type_for(annotation)
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:  # type: ignore[misc]
            required.append(f.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def submit_recipe_tool() -> dict[str, Any]:
    """Build the default Anthropic tool-use definition for ``submit_recipe``.

    Prefer :meth:`AnalysisMode.submit_tool` for mode-aware callers.
    Kept for backwards compatibility with code that doesn't use modes.
    """
    return _default_mode().submit_tool()


# ----------------------------------------------------------------------
# Prompt assembly
# ----------------------------------------------------------------------


def _operation_vocabulary() -> str:
    """Render the curated operation library as a system-prompt section.

    Kept for backwards compatibility. Prefer
    :meth:`AnalysisMode._operation_vocabulary`.
    """
    return _default_mode()._operation_vocabulary()


def build_system_prompt(mode: AnalysisMode | None = None) -> str:
    """Build the system prompt, delegating to the active mode.

    When ``mode`` is ``None``, falls back to the default hypothesis mode
    for backwards compatibility with existing callers.
    """
    if mode is None:
        mode = _default_mode()
    return mode.build_system_prompt()


def build_user_prompt(question: str, catalog: dict[str, dict[str, Any]]) -> str:
    """Per-question prompt: catalog dump + question. Shared across all modes."""
    catalog_str = json.dumps(list(catalog.values()), indent=2, default=str)
    return (
        f"## Available tables\n\n{catalog_str}\n\n## Question\n\n{question}\n\n"
        "Respond by calling `submit_recipe` with a plan, nodes, and final."
    )


# ----------------------------------------------------------------------
# High-level entry points
# ----------------------------------------------------------------------


def ask_for_recipe(
    provider: LLMProvider,
    question: str,
    catalog: dict[str, dict[str, Any]],
    *,
    mode: AnalysisMode | None = None,
) -> dict[str, Any]:
    """Ask the LLM for a recipe payload. Returns the raw tool-input dict.

    Caller is responsible for converting the payload into a ``Recipe``
    instance and validating it.
    """
    if mode is None:
        mode = _default_mode()
    system = mode.build_system_prompt()
    user = build_user_prompt(question, catalog)
    return provider.ask(system=system, user=user, tools=[mode.submit_tool()])


def ask_for_recipe_with_retry(
    provider: LLMProvider,
    question: str,
    catalog: dict[str, dict[str, Any]],
    *,
    mode: AnalysisMode | None = None,
    validate: Any = None,
    max_attempts: int = 2,
) -> tuple[dict[str, Any], list[str]]:
    """Iteration loop (PR 4.4): retry once if the recipe doesn't validate.

    Calls ``validate(payload)`` after each attempt; if it raises, the
    exception message is appended to the user prompt and the LLM is
    asked to fix it. Returns ``(payload, errors)`` where ``errors`` is
    the list of validation errors encountered along the way (empty on
    first-try success). After ``max_attempts``, the most recent payload
    is returned even if still invalid -- caller decides what to do.

    ``validate`` is left abstract so this function stays decoupled from
    Recipe imports; pass ``Recipe.from_payload_and_validate`` (or
    similar) from the call site.
    """
    if mode is None:
        mode = _default_mode()
    system = mode.build_system_prompt()
    user = build_user_prompt(question, catalog)
    tools = [mode.submit_tool()]

    errors: list[str] = []
    payload: dict[str, Any] = {}
    for attempt in range(max_attempts):
        payload = provider.ask(system=system, user=user, tools=tools)
        if validate is None:
            return payload, errors
        try:
            validate(payload)
            return payload, errors
        except Exception as exc:
            errors.append(str(exc))
            if attempt == max_attempts - 1:
                break
            user = (
                f"{user}\n\n## Previous attempt failed validation\n\n"
                f"Error: {exc}\n\nFix the recipe and call submit_recipe again."
            )
    return payload, errors


# ----------------------------------------------------------------------
# Default mode helper
# ----------------------------------------------------------------------


def _default_mode() -> AnalysisMode:
    """Return the hypothesis mode as the default.

    Requires the ``shenas-analysis-hypothesis`` plugin to be installed
    (or another plugin that registers a ``"hypothesis"`` mode).
    """
    from shenas_plugins.core.analytics.mode import get_mode

    return get_mode("hypothesis")
