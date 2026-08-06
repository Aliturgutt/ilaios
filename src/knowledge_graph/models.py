from enum import Enum
from typing import Any


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""
    PROJECT = "Project"
    REPOSITORY = "Repository"
    DIRECTORY = "Directory"
    FILE = "File"
    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"
    TASK = "Task"
    AGENT = "Agent"
    TOOL = "Tool"
    CAPABILITY = "Capability"
    DECISION = "Decision"
    EVIDENCE = "Evidence"
    FACT = "Fact"
    USER = "User"
    MEMORY = "Memory"


class EdgeType(Enum):
    """Types of edges in the knowledge graph."""
    CONTAINS = "contains"
    IMPORTS = "imports"
    CALLS = "calls"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    VERIFIES = "verifies"
    CREATES = "creates"
    USES = "uses"
    BELONGS_TO = "belongs_to"
    REFERENCES = "references"
    DERIVED_FROM = "derived_from"
    RELATED_TO = "related_to"


class Node:
    """A node in the knowledge graph."""

    def __init__(self,
                 node_id: str,
                 node_type: NodeType,
                 properties: dict[str, Any]):
        self.id = node_id
        self.type = node_type
        self.properties = properties


class Edge:
    """An edge in the knowledge graph."""

    def __init__(self,
                 edge_id: str,
                 source_id: str,
                 target_id: str,
                 edge_type: EdgeType,
                 properties: dict[str, Any] | None = None):
        self.id = edge_id
        self.source = source_id
        self.target = target_id
        self.type = edge_type
        self.properties: dict[str, Any] = properties if properties is not None else {}
