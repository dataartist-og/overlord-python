"""
Code Intelligence Layer for Overlord.

Provides framework-aware code analysis, dependency graphs, and MCP server
for agent-accessible ground truth about codebases.
"""

from overlord.code_intelligence.enhanced_blast_radius import EnhancedBlastRadiusEngine
from overlord.code_intelligence.graph_builder import CodeGraphBuilder, FileNode, Symbol
from overlord.code_intelligence.mcp_server import CodeIntelligenceMCP
from overlord.code_intelligence.parsers import (
    DIEdge,
    Entity,
    FrameworkParser,
    Job,
    NestJSParser,
    NextJSParser,
    Route,
)

__all__ = [
    # Graph Builder
    "CodeGraphBuilder",
    "Symbol",
    "FileNode",
    # Parsers
    "FrameworkParser",
    "NextJSParser",
    "NestJSParser",
    "Route",
    "DIEdge",
    "Job",
    "Entity",
    # MCP Server
    "CodeIntelligenceMCP",
    # Enhanced Blast Radius
    "EnhancedBlastRadiusEngine",
]
