"""LLM integration for hypothesis-driven analysis (PR 2.3).

This module is the bridge between the curated analytics vocabulary
(`OPERATIONS`, the catalog, the Recipe DAG) and an LLM. The LLM never
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

3. :func:`build_system_prompt` -- assembles a static system prompt
   describing the operation vocabulary and the catalog format.

4. :func:`build_user_prompt` -- assembles the per-question payload:
   the user's question + the current catalog dump.

5. :func:`operation_tool_schema` -- derives an Anthropic tool-use
   ``input_schema`` from the curated ``OPERATIONS`` registry by walking
   each Operation dataclass's fields. The shape is intentionally
   permissive (recipe nodes are validated post-hoc by ``Recipe.validate``).

The LLM-driven mutation ``askHypothesis`` lives in
``app/graphql/mutations.py`` and uses :func:`ask_for_recipe` here.
"""

from __future__ import annotations

import dataclasses
import json
import os
from typing import Any, ClassVar, Protocol

from shenas_plugins.core.analytics.operations import OPERATIONS, Operation

# ----------------------------------------------------------------------
# Provider interface
# ----------------------------------------------------------------------


class LLMProvider(Protocol):
    """Minimal interface every LLM provider must implement."""

    name: str

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Send the prompt + tools to the LLM and return the parsed tool-use payload.

        The implementation MUST instruct the model to respond by calling
        the ``submit_recipe`` tool. The return value is the dict the
        model passed as the tool's input -- caller is responsible for
        validating it against ``Recipe``.
        """
        ...


class FakeProvider:
    """In-process provider for tests. Returns a pre-canned recipe payload."""

    name: ClassVar[str] = "fake@v0"

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[tuple[str, str]] = []

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]]) -> dict[str, Any]:  # noqa: ARG002
        self.calls.append((system, user))
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
    """Build the Anthropic tool-use definition for ``submit_recipe``.

    The tool's input_schema describes the recipe DAG shape. Operations
    are NOT enumerated as a strict ``oneOf`` -- the LLM gets a freeform
    ``params`` object per node, and we validate post-hoc with
    ``Recipe.validate``. This keeps the schema simple and lets us add
    operations without churning the tool definition.
    """
    return {
        "name": "submit_recipe",
        "description": (
            "Submit a Recipe DAG that answers the user's question. Each node is "
            "either a SourceRef (`type: source`, `table: <qualified.name>`) or "
            "an OpCall (`type: op`, `op_name: <name>`, `params: {...}`, "
            "`inputs: [<node_name>...]`). The `final` field names the node "
            "whose result the user sees."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "string",
                    "description": "One-paragraph natural-language plan for how this recipe answers the question.",
                },
                "nodes": {
                    "type": "object",
                    "description": "Map of node name -> node definition (source or op).",
                    "additionalProperties": True,
                },
                "final": {
                    "type": "string",
                    "description": "Name of the node whose result is the answer.",
                },
            },
            "required": ["plan", "nodes", "final"],
        },
    }


# ----------------------------------------------------------------------
# Prompt assembly
# ----------------------------------------------------------------------


def _operation_vocabulary() -> str:
    """Render the curated operation library as a system-prompt section."""
    out: list[str] = ["## Operation vocabulary", ""]
    for op in OPERATIONS:
        params = operation_param_schema(op)
        out.append(f"### `{op.name}` (arity {op.arity})")
        out.append((op.__doc__ or "").strip())
        out.append("")
        out.append(f"params: {json.dumps(params)}")
        if op.accepts:
            out.append(f"accepts kinds: {sorted(op.accepts)}")
        out.append("")
    return "\n".join(out)


def build_system_prompt() -> str:
    """Static system prompt: vocabulary + recipe shape + guardrails."""
    return (
        "You are a data analyst translating natural-language questions about a "
        "personal-data warehouse into structured Recipe DAGs.\n\n"
        "You MUST respond by calling the `submit_recipe` tool. Use only the "
        "operations listed below; do not invent new ones. Do not write SQL.\n\n"
        + _operation_vocabulary()
        + "\n\nRecipe nodes are either:\n"
        '- `{"type": "source", "table": "<schema>.<name>"}` for a raw input\n'
        '- `{"type": "op", "op_name": "<name>", "params": {...}, "inputs": [...]}` for an operation call\n'
        "The `inputs` array names other nodes by key. The `final` field names the node "
        "whose result is the answer.\n"
    )


def build_user_prompt(question: str, catalog: dict[str, dict[str, Any]]) -> str:
    """Per-question prompt: catalog dump + question."""
    catalog_str = json.dumps(list(catalog.values()), indent=2, default=str)
    return (
        f"## Available tables\n\n{catalog_str}\n\n## Question\n\n{question}\n\n"
        "Respond by calling `submit_recipe` with a plan, nodes, and final."
    )


# ----------------------------------------------------------------------
# High-level entry point
# ----------------------------------------------------------------------


def ask_for_recipe(
    provider: LLMProvider,
    question: str,
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Ask the LLM for a recipe payload. Returns the raw tool-input dict.

    Caller is responsible for converting the payload into a ``Recipe``
    instance and validating it.
    """
    system = build_system_prompt()
    user = build_user_prompt(question, catalog)
    return provider.ask(system=system, user=user, tools=[submit_recipe_tool()])
