"""Entry points - main() function for run_agent.py."""

import sys
from typing import Optional

# Import what we need from run_agent context
import fire
import logging
from datetime import datetime
import uuid
import json


def main(
    query: str = None,
    model: str = "anthropic/claude-opus-4.6",
    api_key: str = None,
    base_url: str = "https://openrouter.ai/api/v1",
    max_turns: int = 10,
    enabled_toolsets: str = None,
    disabled_toolsets: str = None,
    list_tools: bool = False,
    save_trajectories: bool = False,
    save_sample: bool = False,
    verbose: bool = False,
    log_prefix_chars: int = 20,
):
    """
    Main function for running the agent directly.

    Args:
        query (str): Natural language query for the agent.
        model (str): Model name to use (OpenRouter format: provider/model).
        api_key (str): API key for authentication.
        base_url (str): Base URL for the model API.
        max_turns (int): Maximum number of API call iterations.
        enabled_toolsets (str): Comma-separated list of toolsets to enable.
        disabled_toolsets (str): Comma-separated list of toolsets to disable.
        list_tools (bool): Just list available tools and exit.
        save_trajectories (bool): Save conversation trajectories to JSONL files.
        save_sample (bool): Save a single trajectory sample.
        verbose (bool): Enable verbose logging.
        log_prefix_chars (int): Number of characters to show in log previews.
    """
    # Import here to avoid circular imports
    from run_agent import AIAgent

    print("🤖 AI Agent with Tool Calling")
    print("=" * 50)

    # Handle tool listing
    if list_tools:
        from tools.model_tools import (
            get_all_tool_names,
            get_toolset_for_tool,
            get_available_toolsets,
        )
        from tools.toolsets import get_all_toolsets, get_toolset_info

        print("📋 Available Tools & Toolsets:")
        print("-" * 50)

        print("\n🎯 Predefined Toolsets (New System):")
        print("-" * 40)
        all_toolsets = get_all_toolsets()

        basic_toolsets = []
        composite_toolsets = []
        scenario_toolsets = []

        for name, toolset in all_toolsets.items():
            info = get_toolset_info(name)
            if info:
                entry = (name, info)
                if name in ["web", "terminal", "vision", "creative", "reasoning"]:
                    basic_toolsets.append(entry)
                elif name in [
                    "research",
                    "development",
                    "analysis",
                    "content_creation",
                    "full_stack",
                ]:
                    composite_toolsets.append(entry)
                else:
                    scenario_toolsets.append(entry)

        print("\n📌 Basic Toolsets:")
        for name, info in basic_toolsets:
            tools_str = (
                ", ".join(info["resolved_tools"]) if info["resolved_tools"] else "none"
            )
            print(f"  • {name:15} - {info['description']}")
            print(f"    Tools: {tools_str}")

        print("\n📂 Composite Toolsets (built from other toolsets):")
        for name, info in composite_toolsets:
            includes_str = ", ".join(info["includes"]) if info["includes"] else "none"
            print(f"  • {name:15} - {info['description']}")
            print(f"    Includes: {includes_str}")
            print(f"    Total tools: {info['tool_count']}")

        print("\n🎭 Scenario-Specific Toolsets:")
        for name, info in scenario_toolsets:
            print(f"  • {name:20} - {info['description']}")
            print(f"    Total tools: {info['tool_count']}")

        print("\n📦 Legacy Toolsets (for backward compatibility):")
        legacy_toolsets = get_available_toolsets()
        for name, info in legacy_toolsets.items():
            status = "✅" if info["available"] else "❌"
            print(f"  {status} {name}: {info['description']}")
            if not info["available"]:
                print(f"    Requirements: {', '.join(info['requirements'])}")

        all_tools = get_all_tool_names()
        print(f"\n🔧 Individual Tools ({len(all_tools)} available):")
        for tool_name in sorted(all_tools):
            toolset = get_toolset_for_tool(tool_name)
            print(f"  📌 {tool_name} (from {toolset})")

        print("\n💡 Usage Examples:")
        print("  # Use predefined toolsets")
        print(
            "  python run_agent.py --enabled_toolsets=research --query='search for Python news'"
        )
        print(
            "  python run_agent.py --enabled_toolsets=development --query='debug this code'"
        )
        print(
            "  python run_agent.py --enabled_toolsets=safe --query='analyze without terminal'"
        )
        print("  ")
        print("  # Combine multiple toolsets")
        print(
            "  python run_agent.py --enabled_toolsets=web,vision --query='analyze website'"
        )
        print("  ")
        print("  # Disable toolsets")
        print(
            "  python run_agent.py --disabled_toolsets=terminal --query='no command execution'"
        )
        print("  ")
        print("  # Run with trajectory saving enabled")
        print("  python run_agent.py --save_trajectories --query='your question here'")
        return

    # Parse toolset selection arguments
    enabled_toolsets_list = None
    disabled_toolsets_list = None

    if enabled_toolsets:
        enabled_toolsets_list = [t.strip() for t in enabled_toolsets.split(",")]
        print(f"🎯 Enabled toolsets: {enabled_toolsets_list}")

    if disabled_toolsets:
        disabled_toolsets_list = [t.strip() for t in disabled_toolsets.split(",")]
        print(f"🚫 Disabled toolsets: {disabled_toolsets_list}")

    if save_trajectories:
        print("💾 Trajectory saving: ENABLED")
        print("   - Successful conversations → trajectory_samples.jsonl")
        print("   - Failed conversations → failed_trajectories.jsonl")

    # Initialize agent with provided parameters
    try:
        agent = AIAgent(
            base_url=base_url,
            model=model,
            api_key=api_key,
            max_iterations=max_turns,
            enabled_toolsets=enabled_toolsets_list,
            disabled_toolsets=disabled_toolsets_list,
            save_trajectories=save_trajectories,
            verbose_logging=verbose,
            log_prefix_chars=log_prefix_chars,
        )
    except RuntimeError as e:
        print(f"❌ Failed to initialize agent: {e}")
        return

    # Use provided query or default
    if query is None:
        user_query = (
            "Tell me about the latest developments in Python 3.13 and what new features "
            "developers should know about. Please search for current information and try it out."
        )
    else:
        user_query = query

    print(f"\n📝 User Query: {user_query}")
    print("\n" + "=" * 50)

    # Run conversation
    result = agent.run_conversation(user_query)

    print("\n" + "=" * 50)
    print("📋 CONVERSATION SUMMARY")
    print("=" * 50)
    print(f"✅ Completed: {result['completed']}")
    print(f"📞 API Calls: {result['api_calls']}")
    print(f"💬 Messages: {len(result['messages'])}")

    if result["final_response"]:
        print("\n🎯 FINAL RESPONSE:")
        print("-" * 30)
        print(result["final_response"])

    # Save sample trajectory to UUID-named file if requested
    if save_sample:
        sample_id = str(uuid.uuid4())[:8]
        sample_filename = f"sample_{sample_id}.json"

        trajectory = agent._convert_to_trajectory_format(
            result["messages"], user_query, result["completed"]
        )

        entry = {
            "conversations": trajectory,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "completed": result["completed"],
            "query": user_query,
        }

        try:
            with open(sample_filename, "w", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, indent=2))
            print(f"\n💾 Sample trajectory saved to: {sample_filename}")
        except Exception as e:
            print(f"\n⚠️ Failed to save sample: {e}")

    print("\n👋 Agent execution completed!")


def run_main():
    """Entry point for __main__."""
    try:
        fire.Fire(main)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Fatal error in agent execution")


__all__ = ["main", "run_main"]
