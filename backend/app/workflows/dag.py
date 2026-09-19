"""Pure workflow directed-acyclic-graph validation and ordering."""

from dataclasses import dataclass
from uuid import UUID

import networkx as nx

from app.core.errors import WorkflowValidationError
from app.domain.models import StageDefinition, StageDependency


@dataclass(frozen=True, slots=True)
class WorkflowGraph:
    """Validated graph with deterministic execution order."""

    execution_order: tuple[UUID, ...]
    roots: tuple[UUID, ...]
    leaves: tuple[UUID, ...]


class WorkflowGraphValidator:
    """Reject unsafe graph structures before publication or execution."""

    def validate(
        self,
        stages: tuple[StageDefinition, ...],
        dependencies: tuple[StageDependency, ...],
    ) -> WorkflowGraph:
        issues: list[str] = []
        if not stages:
            issues.append("at least one stage is required")

        stage_by_id = {stage.id: stage for stage in stages}
        enabled_stages = tuple(stage for stage in stages if stage.is_enabled)
        if stages and not enabled_stages:
            issues.append("at least one stage must be enabled")
        if len(stage_by_id) != len(stages):
            issues.append("stage identifiers must be unique")
        if len({stage.key for stage in stages}) != len(stages):
            issues.append("stage keys must be unique")
        if len({stage.position for stage in stages}) != len(stages):
            issues.append("stage positions must be unique")

        graph: nx.DiGraph[UUID] = nx.DiGraph()
        graph.add_nodes_from(stage.id for stage in enabled_stages)
        seen_edges: set[tuple[UUID, UUID]] = set()
        for dependency in dependencies:
            stage = stage_by_id.get(dependency.stage_definition_id)
            prerequisite = stage_by_id.get(dependency.depends_on_stage_id)
            if stage is None or prerequisite is None:
                issues.append("every dependency endpoint must belong to the workflow version")
                continue
            if dependency.stage_definition_id == dependency.depends_on_stage_id:
                issues.append(f"stage '{stage.key}' cannot depend on itself")
                continue
            edge = (dependency.depends_on_stage_id, dependency.stage_definition_id)
            if edge in seen_edges:
                issues.append(f"dependency '{prerequisite.key}' -> '{stage.key}' is duplicated")
                continue
            seen_edges.add(edge)
            if stage.is_enabled and not prerequisite.is_enabled:
                issues.append(
                    f"enabled stage '{stage.key}' cannot depend on disabled stage "
                    f"'{prerequisite.key}'"
                )
                continue
            if stage.is_enabled and prerequisite.is_enabled:
                graph.add_edge(*edge)

        if not nx.is_directed_acyclic_graph(graph):
            cycle = nx.find_cycle(graph)
            cycle_keys = " -> ".join(stage_by_id[node_id].key for node_id, _ in cycle)
            issues.append(f"workflow contains a dependency cycle: {cycle_keys}")

        if issues:
            raise WorkflowValidationError(tuple(dict.fromkeys(issues)))

        positions = {stage.id: stage.position for stage in enabled_stages}
        execution_order = tuple(
            nx.lexicographical_topological_sort(graph, key=lambda node_id: positions[node_id])
        )
        roots = tuple(node_id for node_id in execution_order if graph.in_degree(node_id) == 0)
        leaves = tuple(node_id for node_id in execution_order if graph.out_degree(node_id) == 0)
        return WorkflowGraph(execution_order=execution_order, roots=roots, leaves=leaves)
