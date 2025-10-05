"""
Example: Code Intelligence in Action

Demonstrates how to use the code intelligence layer to understand
a codebase and compute enhanced blast radius.
"""

import sys
from pathlib import Path

from overlord.code_intelligence import (
    CodeGraphBuilder,
    EnhancedBlastRadiusEngine,
    NextJSParser,
)
from overlord.models import Story, Priority, RiskLevel


def main():
    """Run code intelligence examples."""
    
    print("=" * 70)
    print("Code Intelligence Layer - Example")
    print("=" * 70)
    print()
    
    # Example 1: Parse a Next.js project
    print("Example 1: Parsing Next.js Project")
    print("-" * 70)
    
    # For demo purposes, use current directory or specify your own
    repo_path = input("Enter path to Next.js project (or press Enter to skip): ").strip()
    
    if repo_path and Path(repo_path).exists():
        try:
            parser = NextJSParser(repo_path)
            parser.parse()
            
            print(f"✓ Found {len(parser.routes)} routes")
            print(f"✓ Found {len(parser.di_edges)} DI relationships")
            
            if parser.routes:
                print("\nSample routes:")
                for route in parser.routes[:5]:
                    print(f"  {route.method:6s} {route.path:30s} → {route.handler}")
        except Exception as e:
            print(f"Error parsing: {e}")
    else:
        print("Skipped (no path provided)")
    
    print()
    
    # Example 2: Build code graphs
    print("Example 2: Building Code Graphs")
    print("-" * 70)
    
    if repo_path and Path(repo_path).exists():
        try:
            builder = CodeGraphBuilder(repo_path, framework="nextjs")
            graphs = builder.build_all_graphs()
            
            print(f"✓ File graph: {graphs['files'].number_of_nodes()} nodes")
            print(f"✓ Symbol graph: {graphs['symbols'].number_of_nodes()} nodes")
            print(f"✓ Route graph: {graphs['routes'].number_of_nodes()} nodes")
            print(f"✓ DI graph: {graphs['di'].number_of_nodes()} nodes")
            
            # Show some symbols
            if builder.symbols:
                print("\nSample symbols:")
                for symbol_id, symbol in list(builder.symbols.items())[:5]:
                    print(f"  {symbol.kind:10s} {symbol.name:30s} at {symbol.file_path}:{symbol.start_line}")
        except Exception as e:
            print(f"Error building graphs: {e}")
    else:
        print("Skipped (no path provided)")
    
    print()
    
    # Example 3: Enhanced blast radius
    print("Example 3: Computing Enhanced Blast Radius")
    print("-" * 70)
    
    # Create a sample story
    story = Story(
        title="Add user export functionality",
        user_value="As an admin, I want to export user data as CSV, so I can analyze it offline",
        acceptance_criteria=[
            "Given admin permissions, When I click Export, Then a CSV file downloads",
            "Given the CSV file, When I open it, Then I see all user fields",
            "Given large datasets, When exporting, Then it processes in batches"
        ],
        priority=Priority.P1,
        risk=RiskLevel.MEDIUM
    )
    
    print(f"Story: {story.title}")
    print(f"Priority: {story.priority}, Risk: {story.risk}")
    
    if repo_path and Path(repo_path).exists():
        try:
            # Use the builder from Example 2
            engine = EnhancedBlastRadiusEngine(
                graph_builders={"example-repo": builder}
            )
            
            blast_radius = engine.compute_enhanced_blast_radius(
                story=story,
                repos=["example-repo"],
                depth=3
            )
            
            print(f"\n✓ Blast Radius Computed:")
            print(f"  Total Impact: {blast_radius.total_impact_count} items")
            print(f"  Risk Level: {blast_radius.risk_level}")
            print(f"  Confidence: {blast_radius.confidence:.0%}")
            print(f"  Systems: {len(blast_radius.systems)}")
            print(f"  Modules: {len(blast_radius.modules)}")
            print(f"  APIs: {len(blast_radius.interfaces)}")
            print(f"  Databases: {len(blast_radius.db_objects)}")
            
            if blast_radius.interfaces:
                print(f"\n  Affected APIs:")
                for api in blast_radius.interfaces[:5]:
                    print(f"    - {api}")
            
            if blast_radius.gaps:
                print(f"\n  Analysis Gaps:")
                for gap in blast_radius.gaps:
                    print(f"    - {gap}")
            
            # Get detailed report
            report = engine.get_detailed_impact_report(
                story=story,
                repos=["example-repo"],
                depth=3
            )
            
            if report["recommendations"]:
                print(f"\n  Recommendations:")
                for rec in report["recommendations"]:
                    print(f"    {rec}")
        
        except Exception as e:
            print(f"Error computing blast radius: {e}")
    else:
        print("Skipped (no path provided)")
    
    print()
    
    # Example 4: Finding callers
    print("Example 4: Finding Who Calls What")
    print("-" * 70)
    
    if repo_path and Path(repo_path).exists() and builder.symbols:
        try:
            # Pick a random symbol
            symbol_id = list(builder.symbols.keys())[0]
            symbol = builder.symbols[symbol_id]
            
            print(f"Symbol: {symbol.name} ({symbol.kind})")
            print(f"Location: {symbol.file_path}:{symbol.start_line}")
            
            callers = builder.get_callers(symbol_id)
            if callers:
                print(f"\n✓ Called by {len(callers)} other symbols:")
                for caller_id in callers[:5]:
                    if caller_id in builder.symbols:
                        caller = builder.symbols[caller_id]
                        print(f"  - {caller.name} at {caller.file_path}:{caller.start_line}")
            else:
                print("\n  (No callers found)")
            
            callees = builder.get_callees(symbol_id)
            if callees:
                print(f"\n✓ Calls {len(callees)} other symbols:")
                for callee_id in callees[:5]:
                    if callee_id in builder.symbols:
                        callee = builder.symbols[callee_id]
                        print(f"  - {callee.name} at {callee.file_path}:{callee.start_line}")
            else:
                print("\n  (No callees found)")
        
        except Exception as e:
            print(f"Error analyzing calls: {e}")
    else:
        print("Skipped (no path provided or no symbols)")
    
    print()
    print("=" * 70)
    print("Example complete!")
    print()
    print("Next steps:")
    print("  1. Try with your own repository")
    print("  2. Integrate with Overlord API")
    print("  3. Use MCP server for agent access")
    print("  4. See CODE_INTELLIGENCE_QUICKSTART.md for more examples")
    print("=" * 70)


if __name__ == "__main__":
    main()
