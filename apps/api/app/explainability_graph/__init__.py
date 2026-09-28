"""Closed, deterministic explanations of authoritative academic results."""

from .eligibility import (
    EdgeRelation, ExplainabilityGraph, GraphMode, GraphNodeType,
    build_eligibility_graph, validate_graph,
)

__all__ = [
    "EdgeRelation", "ExplainabilityGraph", "GraphMode", "GraphNodeType",
    "build_eligibility_graph", "validate_graph",
]
