"""Recipe DAG -- a named-node graph of source references and operation calls.

A ``Recipe`` is the structured form an LLM-authored hypothesis takes once
the natural-language question has been resolved into concrete operations.
It's a directed acyclic graph: each node has a name, each node either
*references a source table* (``SourceRef``) or *invokes an operation on
named upstream nodes* (``OpCall``), and one node is marked as the
``final`` output.

Compilation walks the DAG in topological order, instantiates each
operation from its name + scalar params, resolves its inputs by name,
and applies the operation to produce a new ``RecipeNode``. The final
node's ``RecipeNode`` carries the compiled ``ibis.Expr`` ready to
execute or render to SQL.

The DAG topology is what makes two-branch hypotheses representable
("compute weekly_caffeine, compute weekly_sleep, correlate them"). A
flat sequence of operations on a single carrier value can't express
that without smuggling a DAG in via "branch" operations -- so the DAG
shape is load-bearing from day one.

Recipes are JSON-serializable: ``SourceRef`` / ``OpCall`` are frozen
dataclasses with primitive fields, and the operation lookup happens by
``op_name`` against the dynamic operation registry. This is what
makes recipes durable as part of the ``HypothesisRecord`` artifact.
"""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from shenas_plugins.core.analytics.node import RecipeNode
from shenas_plugins.core.analytics.operations import Operation, OperationError, get_operations

if TYPE_CHECKING:
    import ibis.backends.duckdb as ibd


# ----------------------------------------------------------------------
# Operation lookup -- reads from the dynamic registry each time so
# plugin-contributed operations are visible to the compiler.
# ----------------------------------------------------------------------


def _ops_by_name() -> dict[str, type[Operation]]:
    """Return all registered operations keyed by name.

    Called by :meth:`Recipe.validate` and :meth:`Recipe._evaluate_op`
    instead of a static module-level dict so that operations registered
    by analysis plugins after initial import are visible.
    """
    return get_operations()


class RecipeError(Exception):
    """Raised on a structurally-invalid recipe (cycle, dangling input ref,
    unknown operation, missing source table, ...). Distinct from
    :class:`OperationError`, which fires inside an operation's own
    validation logic during compilation."""


# ----------------------------------------------------------------------
# DAG node types
# ----------------------------------------------------------------------


class SourceRef(BaseModel, frozen=True):
    """Leaf node: a reference to an existing table by qualified name.

    The ``table`` is a ``"<schema>.<name>"`` string that the catalog
    resolves to a kind + time_columns + ibis.Table on compile.
    """

    type: Literal["source"] = "source"
    table: str


class OpCall(BaseModel, frozen=True):
    """Inner node: invoke an operation on one or more named upstream nodes.

    Attributes
    ----------
    op_name
        One of the operation names in the dynamic registry
        (e.g. ``"lag"``, ``"join_as_of"``).
    params
        Scalar parameters for the operation's constructor (e.g.
        ``{"column": "caffeine_mg", "n": 1}``). Lists are converted to
        tuples on instantiation since operations are frozen dataclasses.
    inputs
        Names of upstream DAG nodes whose ``RecipeNode``s become the
        positional arguments to the operation's ``apply``. Order matters:
        for arity-2 operations like ``JoinAsOf``, the first input is the
        left side, the second is the right.
    """

    op_name: str
    params: dict[str, Any] = {}
    inputs: tuple[str, ...] = ()
    type: Literal["op"] = "op"


# ----------------------------------------------------------------------
# Recipe -- the DAG itself
# ----------------------------------------------------------------------


class Recipe(BaseModel, frozen=True):
    """A named-node DAG of ``SourceRef``s and ``OpCall``s.

    Attributes
    ----------
    nodes
        ``{name: SourceRef | OpCall}``. Names are local to the recipe and
        only need to be unique within it.
    final
        Name of the node whose output is "the answer." After compilation,
        ``compile(...)`` returns this node's ``RecipeNode``.
    """

    nodes: dict[str, SourceRef | OpCall]
    final: str

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, catalog: dict[str, dict[str, Any]]) -> list[str]:  # ty: ignore[invalid-method-override]
        """Return a list of human-readable error messages.

        Empty list means the recipe is structurally sound and *should*
        compile -- the only remaining failure modes are operation-side
        validation errors raised at compile time (column mismatches,
        kind rejections from the actual ibis schemas, etc.).

        Checks:
            - ``final`` exists in ``nodes``
            - every ``SourceRef.table`` exists in the catalog
            - every ``OpCall.op_name`` is in the operation registry
            - every ``OpCall.inputs`` reference an existing node
            - the DAG has no cycles
            - each ``OpCall``'s arity matches its number of inputs
        """
        errors: list[str] = []
        ops = _ops_by_name()

        if self.final not in self.nodes:
            errors.append(f"final node `{self.final}` not in recipe")

        for name, node in self.nodes.items():
            if isinstance(node, SourceRef):
                if node.table not in catalog:
                    errors.append(f"node `{name}`: source table `{node.table}` not in catalog")
            elif isinstance(node, OpCall):
                op_cls = ops.get(node.op_name)
                if op_cls is None:
                    errors.append(f"node `{name}`: unknown operation `{node.op_name}` (known: {sorted(ops)})")
                    continue
                if len(node.inputs) != op_cls.arity:
                    errors.append(
                        f"node `{name}`: operation `{node.op_name}` requires {op_cls.arity} input(s), got {len(node.inputs)}"
                    )
                errors.extend(
                    f"node `{name}`: input `{input_name}` references an undefined node"
                    for input_name in node.inputs
                    if input_name not in self.nodes
                )

        # Cycle detection (only if no other structural errors so far,
        # because referencing undefined nodes makes topo-sort meaningless).
        if not errors:
            try:
                self._topological_order()
            except RecipeError as exc:
                errors.append(str(exc))

        return errors

    def _topological_order(self) -> list[str]:
        """Return node names in dependency order (sources first, ``final`` last).

        Standard Kahn's algorithm. Raises :class:`RecipeError` on cycles.
        """
        # Build in-degree map and reverse adjacency.
        in_degree: dict[str, int] = dict.fromkeys(self.nodes, 0)
        downstream: dict[str, list[str]] = {name: [] for name in self.nodes}
        for name, node in self.nodes.items():
            if isinstance(node, OpCall):
                for input_name in node.inputs:
                    in_degree[name] += 1
                    if input_name in downstream:
                        downstream[input_name].append(name)

        # Peel off nodes with in-degree 0. Sort the queue alphabetically
        # so the topological order is deterministic across runs (matters
        # for content-hash dedup later).
        ready = sorted(name for name, deg in in_degree.items() if deg == 0)
        order: list[str] = []
        while ready:
            name = ready.pop(0)
            order.append(name)
            for child in downstream[name]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    # Insert in sorted position for determinism.
                    inserted = False
                    for i, existing in enumerate(ready):
                        if child < existing:
                            ready.insert(i, child)
                            inserted = True
                            break
                    if not inserted:
                        ready.append(child)

        if len(order) != len(self.nodes):
            unresolved = sorted(set(self.nodes) - set(order))
            msg = f"recipe has a cycle (unresolved nodes: {unresolved})"
            raise RecipeError(msg)
        return order

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def compile(
        self,
        con: "ibd.Backend",
        catalog: dict[str, dict[str, Any]],
    ) -> RecipeNode:
        """Walk the DAG and produce the final ``RecipeNode``.

        Parameters
        ----------
        con
            An Ibis DuckDB backend (e.g. ``ibis.duckdb.connect(...)``).
            Used to materialise ``SourceRef``s into ``ibis.Table`` objects
            via ``con.table("schema.name")``.
        catalog
            ``{qualified_table_name: table_metadata_dict}`` from
            :meth:`shenas_plugins.core.table.Table.table_metadata`. The
            compiler uses ``kind`` and ``time_columns`` to construct
            ``RecipeNode`` carriers; operations validate against those.

        Raises
        ------
        RecipeError
            On structural problems (validation errors, missing source).
        OperationError
            On operation-side validation errors (kind rejection,
            missing column references) raised by ``Operation.apply``.
        """
        errors = self.validate(catalog)
        if errors:
            joined = "; ".join(errors)
            raise RecipeError(f"recipe validation failed: {joined}")

        resolved: dict[str, RecipeNode] = {}
        for name in self._topological_order():
            node_def = self.nodes[name]
            if isinstance(node_def, SourceRef):
                resolved[name] = self._resolve_source(node_def, con, catalog)
            else:
                resolved[name] = self._evaluate_op(node_def, resolved)

        return resolved[self.final]

    def _resolve_source(
        self,
        node: SourceRef,
        con: "ibd.Backend",
        catalog: dict[str, dict[str, Any]],
    ) -> RecipeNode:
        """Materialise a source-ref into a ``RecipeNode`` via the catalog."""
        meta = catalog[node.table]  # validated above; KeyError shouldn't happen
        # The qualified table name is "schema.table"; ibis.con.table()
        # accepts the unqualified name + a database arg, but the safer
        # path is to split on the dot ourselves.
        if "." in node.table:
            schema, name = node.table.rsplit(".", 1)
        else:
            schema, name = None, node.table
        ibis_table = con.table(name, database=schema) if schema is not None else con.table(name)
        return RecipeNode(
            expr=ibis_table,
            kind=meta.get("kind", "unknown"),
            time_columns=meta.get("time_columns", {}),
            table_ref=node.table,
        )

    def _evaluate_op(
        self,
        node: OpCall,
        resolved: dict[str, RecipeNode],
    ) -> RecipeNode:
        """Instantiate ``node.op_name`` with its scalar params and apply
        it to the resolved upstream ``RecipeNode``s in declared order."""
        op_cls = _ops_by_name()[node.op_name]
        # Convert any list params to tuples since operations are frozen
        # dataclasses (lists aren't hashable). This lets recipes round-trip
        # cleanly through JSON.
        params = {k: (tuple(v) if isinstance(v, list) else v) for k, v in node.params.items()}
        try:
            op = op_cls(**params)
        except TypeError as exc:
            msg = f"node `{node.op_name}`: cannot instantiate with params {params}: {exc}"
            raise RecipeError(msg) from exc
        inputs = [resolved[input_name] for input_name in node.inputs]
        try:
            return op.apply(*inputs)
        except OperationError:
            raise  # propagate operation-side errors as-is
        except Exception as exc:
            msg = f"node `{node.op_name}`: apply failed: {exc}"
            raise RecipeError(msg) from exc

    def to_sql(
        self,
        con: "ibd.Backend",
        catalog: dict[str, dict[str, Any]],
        *,
        dialect: str = "duckdb",
    ) -> str:
        """Compile and return the SQL for the final node.

        Convenience wrapper around ``ibis.to_sql(self.compile(...).expr)``.
        Useful for "show your work" UIs and for debugging recipes without
        executing them.
        """
        import ibis

        result = self.compile(con, catalog)
        return str(ibis.to_sql(result.expr, dialect=dialect))
