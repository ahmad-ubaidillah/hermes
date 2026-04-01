#!/usr/bin/env python3
"""Hermes REPL - Interactive Python REPL for debugging and exploration.

Usage:
    python repl.py                    # Start REPL
    python repl.py --session abc123   # Resume session
    python repl.py --model opencode/qwen3.6-plus-free  # Use specific model

Features:
    - Auto-import Hermes modules
    - Tab completion for tools, skills, functions
    - Syntax highlighting (via Pygments if available)
    - Multi-line input support
    - Session persistence with history
    - Quick chat function: chat("message") -> response
    - Tools listing: tools() -> list all available tools
    - Models listing: models() -> list available models
    - Session info: session() -> current session details
"""

from __future__ import annotations

import ast
import atexit
import code
import importlib
import json
import os
import readline
import rlcompleter
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# Hermes imports (lazy)
HERMES_MODULES = {
    "agent": "run_agent",
    "registry": "tools.registry",
    "session_db": "core.hermes_state",
    "config": "hermes_cli.config",
    "gateway": "gateway.run",
}

# Try to import Pygments for syntax highlighting
try:
    from pygments import highlight
    from pygments.lexers import PythonLexer, PythonTracebackLexer
    from pygments.formatters import Terminal256Formatter

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


def _syntax_highlight(text: str, is_traceback: bool = False) -> str:
    """Apply syntax highlighting if Pygments is available."""
    if not PYGMENTS_AVAILABLE:
        return text
    try:
        lexer = PythonTracebackLexer() if is_traceback else PythonLexer()
        formatter = Terminal256Formatter(style="monokai")
        return highlight(text, lexer, formatter).rstrip("\n")
    except Exception:
        return text


class HermesCompleter:
    """Enhanced tab completer for Hermes REPL."""

    def __init__(self, repl_instance):
        self.repl = repl_instance
        self.base_completer = rlcompleter.Completer(repl_instance.locals)

    def complete(self, text, state):
        """Custom completion that includes Hermes commands and modules."""
        # If we're at the start of a line, offer built-in commands
        if not text or readline.get_line_buffer().strip() == text:
            commands = [
                "help()",
                "tools()",
                "models()",
                "session()",
                "chat(",
                "clear()",
                "exit()",
                "quit()",
            ]
            matches = [c for c in commands if c.startswith(text)]
            if state < len(matches):
                return matches[state]

        # Fall back to standard Python completion
        return self.base_completer.complete(text, state)


class HermesREPL:
    """Interactive REPL for Hermes with auto-imports and debugging tools."""

    def __init__(
        self,
        model: str = "opencode/qwen3.6-plus-free",
        session_id: Optional[str] = None,
        hermes_home: Optional[Path] = None,
    ):
        self.model = model
        self.session_id = session_id
        self.hermes_home = hermes_home or Path.home() / ".hermes"

        self.locals: Dict[str, Any] = {}
        self.agent = None
        self.history_file = self.hermes_home / "repl_history"
        self._multiline_buffer = ""
        self._in_multiline = False

        self._setup_environment()
        self._setup_readline()
        self._load_history()

    def _setup_environment(self):
        """Setup environment variables and imports."""
        if self.hermes_home:
            os.environ["HERMES_HOME"] = str(self.hermes_home)

        # Add Hermes to path
        hermes_root = Path(__file__).parent
        if str(hermes_root) not in sys.path:
            sys.path.insert(0, str(hermes_root))

        # Pre-import common modules
        print("Loading Hermes modules...")

        # Standard library
        import json
        import os
        import sys
        from pathlib import Path
        from datetime import datetime

        self.locals.update(
            {
                "json": json,
                "os": os,
                "sys": sys,
                "Path": Path,
                "datetime": datetime,
            }
        )

        # Try to import Hermes modules
        imports = [
            ("AIAgent", "run_agent", "AIAgent"),
            ("registry", "tools.registry", "registry"),
            ("SessionDB", "core.hermes_state", "SessionDB"),
            ("load_config", "hermes_cli.config", "load_config"),
        ]

        for name, module, attr in imports:
            try:
                mod = importlib.import_module(module)
                self.locals[name] = getattr(mod, attr) if attr != name else mod
                print(f"  ✓ {name}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")

        # Helper functions
        self.locals.update(
            {
                "help": self._help,
                "tools": self._list_tools,
                "models": self._list_models,
                "session": self._session_info,
                "chat": self._quick_chat,
                "clear": lambda: os.system("clear"),
                "exit": lambda: sys.exit(0),
                "quit": lambda: sys.exit(0),
            }
        )

        # Load agent if session_id provided
        if self.session_id:
            self._load_session()

    def _setup_readline(self):
        """Setup readline for tab completion and history."""
        # Custom completer
        completer = HermesCompleter(self)
        readline.set_completer(completer.complete)
        readline.set_completer_delims(readline.get_completer_delims().replace("-", ""))
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")
        readline.parse_and_bind("set show-all-if-ambiguous on")

        # Multi-line support
        readline.parse_and_bind("bind ^R reverse-search-history")

    def _load_history(self):
        """Load command history."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            if self.history_file.exists():
                readline.read_history_file(str(self.history_file))
        except Exception:
            pass  # History is optional

        atexit.register(self._save_history)

    def _save_history(self):
        """Save command history."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            readline.write_history_file(str(self.history_file))
        except Exception:
            pass  # History save failure is non-critical

    def _help(self):
        """Show REPL help."""
        help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    HERMES REPL HELP                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Built-in Commands:                                          ║
║    help()      - Show this help                              ║
║    tools()     - List available tools                        ║
║    models()    - List available models                       ║
║    session()   - Show session info                           ║
║    chat(msg)   - Quick chat with Hermes                      ║
║    clear()     - Clear screen                                ║
║    exit()      - Exit REPL                                   ║
║                                                              ║
║  Pre-imported Modules:                                       ║
║    AIAgent     - Main agent class                            ║
║    registry    - Tool registry                               ║
║    SessionDB   - Session database                            ║
║    load_config - Load Hermes config                          ║
║                                                              ║
║  Examples:                                                   ║
║    >>> agent = AIAgent(model="anthropic/claude-sonnet-4")    ║
║    >>> response = agent.chat("Hello!")                       ║
║    >>> tools = registry._tools.keys()                        ║
║    >>> db = SessionDB()                                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(help_text)

    def _list_tools(self) -> List[str]:
        """List available tools."""
        try:
            tools = list(self.locals["registry"]._tools.keys())
            print(f"Available tools ({len(tools)}):")
            for i, tool in enumerate(sorted(tools), 1):
                entry = self.locals["registry"]._tools.get(tool)
                desc = entry.description if entry else ""
                desc_preview = f" — {desc[:60]}" if desc else ""
                print(f"  {i:3}. {tool}{desc_preview}")
            return tools
        except Exception as e:
            print(f"Error listing tools: {e}")
            return []

    def _list_models(self) -> List[str]:
        """List available models from Hermes config."""
        try:
            # Try to load models from the Hermes model catalog
            from hermes_cli.models import OPENROUTER_MODELS, _PROVIDER_MODELS

            all_models = []
            for model_id, desc in OPENROUTER_MODELS:
                all_models.append(model_id)
            # Add provider-specific models
            for provider, models in _PROVIDER_MODELS.items():
                for m in models:
                    if "/" not in m:  # Not already provider-prefixed
                        all_models.append(f"{provider}/{m}")
            # Deduplicate
            seen = set()
            unique_models = []
            for m in all_models:
                if m not in seen:
                    seen.add(m)
                    unique_models.append(m)
        except Exception:
            # Fallback to hardcoded list
            unique_models = [
                "anthropic/claude-sonnet-4",
                "anthropic/claude-opus-4",
                "openai/gpt-4o",
                "openai/gpt-4-turbo",
                "opencode/qwen3.6-plus-free",
                "opencode/mimo-v2-omni-free",
                "opencode/minimax-m2.5-free",
            ]

        print("Available models:")
        for m in unique_models:
            marker = " ← current" if m == self.model else ""
            print(f"  - {m}{marker}")
        return unique_models

    def _session_info(self):
        """Show session info."""
        print(f"Session ID: {self.session_id or 'none'}")
        print(f"Model: {self.model}")
        print(f"HERMES_HOME: {self.hermes_home}")
        if self.agent:
            print(f"Agent: initialized")
            print(
                f"History: {len(self.agent._session_messages) if hasattr(self.agent, '_session_messages') else 0} messages"
            )
            print(f"Tokens: {getattr(self.agent, 'session_total_tokens', 0)} total")
        else:
            print("Agent: not initialized")

        # Show session from DB if available
        if self.session_id:
            try:
                SessionDB = self.locals.get("SessionDB")
                if SessionDB:
                    db = SessionDB()
                    session = db.get_session(self.session_id)
                    if session:
                        print(f"\nSession from DB:")
                        print(f"  Source: {session.get('source', 'unknown')}")
                        print(f"  Started: {session.get('started_at', 'unknown')}")
                        print(f"  Messages: {session.get('message_count', 0)}")
            except Exception as e:
                print(f"\n  (Could not load session from DB: {e})")

    def _quick_chat(self, message: str) -> str:
        """Quick chat with Hermes agent."""
        if not self.agent:
            print("Initializing agent...")
            try:
                AIAgent = self.locals["AIAgent"]
                self.agent = AIAgent(model=self.model, quiet_mode=True)
                print("Agent initialized.")
            except Exception as e:
                print(f"Failed to initialize agent: {e}")
                return ""

        print(f"\n[User]: {message}")
        try:
            response = self.agent.chat(message)
            print(f"\n[Hermes]: {_syntax_highlight(response)}")
            return response
        except Exception as e:
            print(f"Error: {e}")
            return ""

    def _load_session(self):
        """Load existing session."""
        try:
            SessionDB = self.locals["SessionDB"]
            db = SessionDB()
            session = db.get_session(self.session_id)
            if session:
                print(f"Loaded session: {self.session_id}")
                print(f"  Source: {session.get('source', 'unknown')}")
                print(f"  Messages: {session.get('message_count', 0)}")
            else:
                print(f"Session not found: {self.session_id}")
        except Exception as e:
            print(f"Error loading session: {e}")

    def _is_complete_statement(self, text: str) -> bool:
        """Check if the input is a complete Python statement."""
        try:
            ast.parse(text)
            return True
        except SyntaxError:
            return False

    def run(self):
        """Run the interactive REPL."""
        banner = (
            """
╔══════════════════════════════════════════════════════════════╗
║                    HERMES REPL v1.0                          ║
╠══════════════════════════════════════════════════════════════╣
║  Interactive Python REPL for Hermes Agent                    ║
║  Type help() for commands, exit() to quit                    ║
║  Syntax highlighting: """
            + (
                "enabled"
                if PYGMENTS_AVAILABLE
                else "disabled (pip install pygments)                "
            )
            + """║
╚══════════════════════════════════════════════════════════════╝
"""
        )
        print(banner)
        print(f"Model: {self.model}")
        print(f"Session: {self.session_id or 'new'}")
        print()

        # Create interactive console
        console = code.InteractiveConsole(self.locals)

        # Custom raw_input with better prompt
        def get_input(prompt: str) -> str:
            try:
                return input(prompt)
            except EOFError:
                print("\nExiting...")
                sys.exit(0)
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt")
                return ""

        # Run REPL loop
        while True:
            try:
                line = get_input("hermes>>> ")

                if not line.strip():
                    if self._in_multiline:
                        # Empty line in multiline mode - execute buffer
                        break
                    continue

                # Handle special commands (only at top level)
                if not self._in_multiline and line.strip() in ["exit", "quit"]:
                    print("Goodbye!")
                    break

                # Multi-line handling
                if self._in_multiline:
                    self._multiline_buffer += "\n" + line
                    if self._is_complete_statement(self._multiline_buffer):
                        # Execute the complete block
                        try:
                            try:
                                ast.parse(self._multiline_buffer, mode="eval")
                                result = eval(self._multiline_buffer, self.locals)
                                if result is not None:
                                    print(_syntax_highlight(repr(result)))
                            except SyntaxError:
                                console.runcode(self._multiline_buffer)
                        except Exception:
                            traceback.print_exc()
                        finally:
                            self._multiline_buffer = ""
                            self._in_multiline = False
                    continue

                # Try to execute
                try:
                    # Check if it's an expression
                    try:
                        ast.parse(line, mode="eval")
                        # It's an expression, evaluate and print
                        result = eval(line, self.locals)
                        if result is not None:
                            print(_syntax_highlight(repr(result)))
                    except SyntaxError:
                        # Check if it's a complete statement
                        if self._is_complete_statement(line):
                            console.runcode(line)
                        else:
                            # Start multi-line mode
                            self._multiline_buffer = line
                            self._in_multiline = True
                            print("... ")
                            continue
                except Exception:
                    traceback.print_exc()

            except KeyboardInterrupt:
                if self._in_multiline:
                    print("\nCancelled multi-line input.")
                    self._multiline_buffer = ""
                    self._in_multiline = False
                else:
                    print("\nKeyboardInterrupt (Ctrl-D to exit)")
                continue


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Hermes Interactive REPL")
    parser.add_argument(
        "--model", default="opencode/qwen3.6-plus-free", help="Model to use"
    )
    parser.add_argument("--session", help="Resume session ID")
    parser.add_argument("--hermes-home", type=Path, help="HERMES_HOME path")
    args = parser.parse_args()

    repl = HermesREPL(
        model=args.model,
        session_id=args.session,
        hermes_home=args.hermes_home,
    )
    repl.run()


if __name__ == "__main__":
    main()
