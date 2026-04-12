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

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]], tool_name: str | None = None) -> dict[str, Any]:
        """Send the prompt + tools to the LLM and return the parsed tool-use payload.

        The model is forced to call a specific tool via ``tool_choice``.
        If ``tool_name`` is given it selects that tool; otherwise the
        first tool in ``tools`` is used. The return value is the dict
        the model passed as the tool's input -- caller is responsible
        for validating it. Implementations should also update
        ``last_input_tokens`` / ``last_output_tokens`` so the caller
        can record cost.
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

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]], tool_name: str | None = None) -> dict[str, Any]:  # noqa: ARG002
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

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]], tool_name: str | None = None) -> dict[str, Any]:
        try:
            import anthropic  # ty: ignore[unresolved-import]
        except ImportError as exc:
            msg = "anthropic SDK not installed; pip install anthropic"
            raise RuntimeError(msg) from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "ANTHROPIC_API_KEY not set"
            raise RuntimeError(msg)

        forced_name = tool_name or tools[0]["name"]
        client = anthropic.Anthropic(api_key=api_key)
        # Force the LLM to call the first tool in the list.
        tool_name = tools[0]["name"] if tools else "submit_recipe"
        resp = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=tools,
            tool_choice={"type": "tool", "name": forced_name},
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.last_input_tokens = int(getattr(usage, "input_tokens", 0))
            self.last_output_tokens = int(getattr(usage, "output_tokens", 0))
        # Find the tool_use block matching the forced tool name.
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == forced_name:
                return dict(block.input)
        msg = f"LLM did not call {forced_name}; got {resp.content!r}"
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
    from shenas_plugins.core.analytics.operations import get_operations

    for op in get_operations().values():
        params = operation_param_schema(op)
        out.append(f"### `{op.name}` (arity {op.arity})")
        out.append((op.__doc__ or "").strip())
        out.append("")
        out.append(f"params: {json.dumps(params)}")
        if op.accepts:
            out.append(f"accepts kinds: {sorted(op.accepts)}")
        out.append("")
    return "\n".join(out)


def _research_context(findings: list[str] | None) -> str:
    """Render literature findings as a system-prompt section."""
    if not findings:
        return ""
    lines = [
        "\n\n## Research context\n",
        "The following published findings are relevant to the user's data sources.",
        "Use them to inform your recipe design: prefer temporal lags supported by",
        "evidence, consider confounders mentioned in the mechanisms, and note",
        "evidence strength when choosing between alternative hypotheses.\n",
    ]
    lines.extend(f"- {f}" for f in findings)
    return "\n".join(lines) + "\n"


def build_system_prompt(
    mode: AnalysisMode | None = None,
    *,
    findings: list[str] | None = None,
) -> str:
    """Static system prompt: vocabulary + recipe shape + guardrails.

    Parameters
    ----------
    mode
        If provided, delegates to ``mode.build_system_prompt()`` and
        appends research context. Otherwise falls back to the default
        vocabulary-based prompt.
    findings
        Pre-rendered finding lines (from ``Finding.to_prompt_line()``).
        Appended as a ``## Research context`` section so the LLM uses
        evidence-informed lags and effect directions.
    """
    if mode is not None:
        return mode.build_system_prompt() + _research_context(findings)
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
        "whose result is the answer.\n" + _research_context(findings)
    )


def build_user_prompt(
    question: str,
    catalog: dict[str, dict[str, Any]],
    *,
    relevant_findings: list[str] | None = None,
) -> str:
    """Per-question prompt: catalog dump + question-specific findings + question.

    Parameters
    ----------
    relevant_findings
        Pre-rendered finding lines specifically matched to this question
        (from ``Finding.for_question()`` -> ``to_prompt_line()``).
    """
    catalog_str = json.dumps(list(catalog.values()), indent=2, default=str)
    parts = [f"## Available tables\n\n{catalog_str}\n\n"]
    if relevant_findings:
        parts.append("## Relevant research for this question\n\n")
        parts.extend(f"- {line}\n" for line in relevant_findings)
        parts.append("\n")
    parts.append(f"## Question\n\n{question}\n\n")
    parts.append("Respond by calling `submit_recipe` with a plan, nodes, and final.")
    return "".join(parts)


# ----------------------------------------------------------------------
# High-level entry point
# ----------------------------------------------------------------------


def ask_for_recipe(
    provider: LLMProvider,
    question: str,
    catalog: dict[str, dict[str, Any]],
    *,
    mode: AnalysisMode | None = None,
    findings: list[str] | None = None,
    relevant_findings: list[str] | None = None,
) -> dict[str, Any]:
    """Ask the LLM for a recipe payload. Returns the raw tool-input dict.

    Caller is responsible for converting the payload into a ``Recipe``
    instance and validating it.

    Parameters
    ----------
    mode
        If provided, uses the mode's system prompt and tool definition.
    findings
        All findings for the system prompt (broad context).
    relevant_findings
        Question-specific findings for the user prompt.
    """
    system = build_system_prompt(mode, findings=findings)
    user = build_user_prompt(question, catalog, relevant_findings=relevant_findings)
    tool = mode.submit_tool() if mode is not None else submit_recipe_tool()
    return provider.ask(system=system, user=user, tools=[tool])


def ask_for_recipe_with_retry(
    provider: LLMProvider,
    question: str,
    catalog: dict[str, dict[str, Any]],
    *,
    mode: AnalysisMode | None = None,
    validate: Any = None,
    max_attempts: int = 2,
    findings: list[str] | None = None,
    relevant_findings: list[str] | None = None,
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

    Parameters
    ----------
    mode
        If provided, uses the mode's system prompt and tool definition.
    findings
        All findings for the system prompt (broad context).
    relevant_findings
        Question-specific findings for the user prompt.
    """
    system = build_system_prompt(mode, findings=findings)
    user = build_user_prompt(question, catalog, relevant_findings=relevant_findings)
    tools = [mode.submit_tool() if mode is not None else submit_recipe_tool()]

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
# Interpretation: compare results to literature
# ----------------------------------------------------------------------


def ask_for_interpretation(
    provider: LLMProvider,
    question: str,
    result: dict[str, Any],
    *,
    findings: list[str] | None = None,
) -> str:
    """Ask the LLM to interpret a hypothesis result in context of research literature.

    Returns a narrative interpretation comparing the user's personal
    data result against published findings. The LLM is forced to call
    the ``submit_interpretation`` tool so we get clean text back.

    Parameters
    ----------
    provider
        The LLM provider.
    question
        The user's original question.
    result
        The result dict (from ``Result.to_dict()``).
    findings
        Pre-rendered finding lines relevant to the question.
    """
    system = (
        "You are a data analyst interpreting personal data analysis results. "
        "Compare the user's result against published research findings. "
        "Note where the personal data agrees or disagrees with the literature, "
        "suggest possible explanations for discrepancies, and flag caveats "
        "(sample size, confounders, reverse causation). Be concise and specific. "
        "You MUST respond by calling the `submit_interpretation` tool."
    )

    parts = [f"## Question\n\n{question}\n\n"]
    parts.append(f"## Result\n\n{json.dumps(result, indent=2, default=str)}\n\n")
    if findings:
        parts.append("## Relevant published findings\n\n")
        parts.extend(f"- {line}\n" for line in findings)
    user = "".join(parts)

    tool = {
        "name": "submit_interpretation",
        "description": "Submit your narrative interpretation of the result in context of the research literature.",
        "input_schema": {
            "type": "object",
            "properties": {
                "interpretation": {
                    "type": "string",
                    "description": "Narrative interpretation comparing the personal data result to published literature.",
                },
            },
            "required": ["interpretation"],
        },
    }

    try:
        payload = provider.ask(system=system, user=user, tools=[tool])
        return payload.get("interpretation", "")
    except Exception:
        return ""
