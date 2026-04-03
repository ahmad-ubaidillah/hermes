"""Aizen Agent Dashboard TUI — Full-screen multi-panel dashboard.

Replaces the linear REPL layout with a dashboard matching design.md:

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🤖 AIZEN-OS v3.0.0  [●] MULTI-AGENT MODE     [Session: API-Auth-Security]    │
└──────────────────────┬───────────────────────────────────────────────────────┘
│ 👥 AGENT FLEET       │ 🚀 LIVE AGENT ACTIVITY                                │
├──────────────────────┤                                                       │
│ 🟡 MANAGER  [Plan]   │  1. 🟦 ACTIVE AGENT  : [ CODER-02 ]                   │
│ 🔵 CODER    [Work]   │  2. 📋 CURRENT TASK  : [#04 JWT Rotation Logic]       │
│ 🟢 TESTER   [Idle]   │  3. 🛠️  ACTION       : [ Refactoring `auth.rs` ]      │
│ ⚪ REVIEWER [Wait]   │  4. 📂 LOCATION     : [ /src/services/auth.rs ]      │
├──────────────────────┤  5. 📊 STATUS       : [ ██████████░░░░ ] 65%         │
│ 🌐 CONTEXT & TOOLS   │                                                       │
├──────────────────────┤ ───────────────────────────────────────────────────── │
│ 🧠 Mem: Long-Term    │ 💬 INTERACTION                                        │
│ 🛠️  Active Tools:    │                                                       │
│   ├─ RipGrep         │ MANAGER: "Coder sedang mengimplementasikan RS256.     │
│   ├─ Hop-Testing     │          Setelah selesai, Tester akan mengambil alih  │
│   └─ Shell-Exec      │          untuk validasi payload."                     │
├──────────────────────┤                                                       │
│ 📋 QUICK TASKS       │                                                       │
├──────────────────────┤                                                       │
│ [ ] #04 JWT-Rot      │                                                       │
│ [ ] #05 Refactor     │                                                       │
│ [ ] #06 Fix-API      │                                                       │
│ [x] #01 Setup        │                                                       │
└──────────────────────┴───────────────────────────────────────────────────────┐
│ ⚡ FOCUS: [ CODER is writing unit tests for JWT validation...             ] │
├──────────────────────────────────────────────────────────────────────────────┤
│ ⌨️ INPUT: [ increase worker threads to 4 ]                                   │
└──────────────────────────────────────────────────────────────────────────────┘
 [F1] Help [F2] Kanban View [F3] Agent Logs [F4] Tools Config [C-c] Stop
"""

import logging
import shutil
import time
from typing import Optional

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    Layout,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import (
    BufferControl,
    FormattedTextControl,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import (
    ConditionalProcessor,
    PasswordProcessor,
    Processor,
    Transformation,
)
from prompt_toolkit.widgets import TextArea

from aizen_cli.commands import SlashCommandAutoSuggest, SlashCommandCompleter

logger = logging.getLogger(__name__)

# ── Color constants (overridden by skin engine) ──────────────────────────────

_DASHBOARD_COLORS = {
    "header_border": "#FFD700",
    "header_title": "#FFD700",
    "header_text": "#FFF8DC",
    "header_dim": "#B8860B",
    "sidebar_border": "#CD7F32",
    "sidebar_title": "#FFBF00",
    "sidebar_text": "#FFF8DC",
    "sidebar_dim": "#B8860B",
    "panel_border": "#CD7F32",
    "panel_title": "#FFD700",
    "panel_text": "#FFF8DC",
    "panel_dim": "#B8860B",
    "interaction_border": "#CD7F32",
    "interaction_title": "#FFD700",
    "interaction_text": "#FFF8DC",
    "interaction_dim": "#B8860B",
    "interaction_user": "#FFBF00",
    "interaction_assistant": "#FFF8DC",
    "interaction_tool": "#888888",
    "focus_border": "#CD7F32",
    "focus_text": "#FFBF00",
    "input_border": "#CD7F32",
    "input_prompt": "#FFF8DC",
    "input_text": "#FFF8DC",
    "input_placeholder": "#555555",
    "func_key": "#B8860B",
    "func_key_dim": "#666666",
    "progress_filled": "#FFD700",
    "progress_empty": "#333333",
    "status_yellow": "#FFD700",
    "status_blue": "#4A90D9",
    "status_green": "#4CAF50",
    "status_white": "#AAAAAA",
    "status_red": "#FF6B6B",
    "completion_menu": "bg:#1a1a2e #FFF8DC",
    "completion_menu_current": "bg:#333355 #FFD700",
}


def _get_skin_colors():
    """Load colors from the active skin, falling back to defaults."""
    colors = dict(_DASHBOARD_COLORS)
    try:
        from aizen_cli.skin_engine import get_active_skin

        skin = get_active_skin()
        # Map skin colors to dashboard colors
        skin_color_map = {
            "banner_border": "header_border",
            "banner_title": "header_title",
            "banner_text": "header_text",
            "banner_dim": "header_dim",
            "ui_accent": "panel_border",
            "input_rule": "input_border",
            "prompt": "input_text",
        }
        for skin_key, dash_key in skin_color_map.items():
            val = skin.colors.get(skin_key)
            if val:
                colors[dash_key] = val
    except Exception:
        pass
    return colors


# ── Helper: box drawing ──────────────────────────────────────────────────────


def _hline(n: int) -> str:
    return "─" * max(0, n)


def _vline() -> str:
    return "│"


def _corner_tl() -> str:
    return "┌"


def _corner_tr() -> str:
    return "┐"


def _corner_bl() -> str:
    return "└"


def _corner_br() -> str:
    return "┘"


def _t_down() -> str:
    return "┬"


def _t_up() -> str:
    return "┴"


def _t_right() -> str:
    return "├"


def _t_left() -> str:
    return "┤"


def _cross() -> str:
    return "┼"


# ── DashboardTUI class ───────────────────────────────────────────────────────


class DashboardTUI:
    """Full-screen dashboard TUI for Aizen Agent.

    Manages the entire prompt_toolkit application with a multi-panel layout.
    """

    def __init__(self, cli_ref):
        """Initialize the dashboard TUI.

        Args:
            cli_ref: Reference to the AizenCLI instance for state access.
        """
        self._cli = cli_ref
        self._colors = _get_skin_colors()
        self._app: Optional[Application] = None
        self._should_exit = False
        self._last_invalidate = 0.0

        # State
        self._version = "3.0.0"
        self._mode = "MULTI-AGENT MODE"
        self._session_name = ""
        self._agent_fleet = [
            {"name": "MANAGER", "status": "Plan", "color": "yellow"},
            {"name": "CODER", "status": "Work", "color": "blue"},
            {"name": "TESTER", "status": "Idle", "color": "green"},
            {"name": "REVIEWER", "status": "Wait", "color": "white"},
        ]
        self._live_activity = {
            "agent": "CODER-02",
            "task": "#04 JWT Rotation Logic",
            "action": "Refactoring `auth.rs`",
            "location": "/src/services/auth.rs",
            "progress": 65,
        }
        self._interactions: list[dict] = []
        self._tools: list[str] = ["RipGrep", "Hop-Testing", "Shell-Exec"]
        self._memory_status = "Long-Term"
        self._tasks: list[dict] = [
            {"id": "#04", "label": "JWT-Rot", "done": False},
            {"id": "#05", "label": "Refactor", "done": False},
            {"id": "#06", "label": "Fix-API", "done": False},
            {"id": "#01", "label": "Setup", "done": True},
        ]
        self._focus_text = ""
        self._function_keys = [
            ("F1", "Help"),
            ("F2", "Kanban View"),
            ("F3", "Agent Logs"),
            ("F4", "Tools Config"),
            ("C-c", "Stop"),
        ]

        # Layout dimensions
        self._sidebar_width = 24

    # ── Public API ───────────────────────────────────────────────────────────

    def update_agent_fleet(self, agents: list[dict]):
        """Update the agent fleet panel.

        Args:
            agents: List of dicts with keys: name, status, color.
                    color is one of: yellow, blue, green, white, red.
        """
        if agents:
            self._agent_fleet = agents
        self._invalidate()

    def update_live_activity(self, activity: dict):
        """Update the live activity section.

        Args:
            activity: Dict with optional keys: agent, task, action,
                      location, progress (0-100).
        """
        if activity:
            self._live_activity.update(activity)
        self._invalidate()

    def add_interaction(self, role: str, content: str):
        """Add a message to the interaction area.

        Args:
            role: One of 'user', 'assistant', 'system', 'tool'.
            content: The message content.
        """
        self._interactions.append({"role": role, "content": content})
        # Keep last 50 interactions to avoid memory issues
        if len(self._interactions) > 50:
            self._interactions = self._interactions[-50:]
        self._invalidate()

    def update_tasks(self, tasks: list[dict]):
        """Update the quick tasks panel.

        Args:
            tasks: List of dicts with keys: id, label, done.
        """
        if tasks:
            self._tasks = tasks
        self._invalidate()

    def update_tools(self, tools: list[str]):
        """Update the active tools list.

        Args:
            tools: List of tool names.
        """
        if tools:
            self._tools = tools
        self._invalidate()

    def set_focus(self, text: str):
        """Update the focus line text."""
        self._focus_text = text
        self._invalidate()

    def set_session_name(self, name: str):
        """Update the session name in the header."""
        self._session_name = name
        self._invalidate()

    def set_mode(self, mode: str):
        """Update the mode text in the header."""
        self._mode = mode
        self._invalidate()

    def set_function_keys(self, keys: list[tuple[str, str]]):
        """Update the function key bar.

        Args:
            keys: List of (key, label) tuples.
        """
        if keys:
            self._function_keys = keys
        self._invalidate()

    def set_memory_status(self, status: str):
        """Update the memory status in Context & Tools."""
        self._memory_status = status
        self._invalidate()

    def invalidate(self):
        """Trigger a re-render."""
        self._invalidate()

    def _invalidate(self, min_interval: float = 0.15):
        """Throttled UI repaint."""
        now = time.monotonic()
        if self._app and (now - self._last_invalidate) >= min_interval:
            self._last_invalidate = now
            self._app.invalidate()

    def stop(self):
        """Exit the event loop."""
        self._should_exit = True
        if self._app and self._app.is_running:
            try:
                self._app.exit()
            except Exception:
                pass

    # ── Layout building ──────────────────────────────────────────────────────

    def _get_terminal_size(self):
        """Get current terminal dimensions."""
        try:
            return shutil.get_terminal_size((100, 30))
        except Exception:
            return type("Size", (), {"columns": 100, "lines": 30})()

    def _build_header(self) -> FormattedText:
        """Build the header bar row."""
        cols = self._get_terminal_size().columns
        c = self._colors

        # Build header content
        header_text = f"🤖 AIZEN-OS v{self._version}"
        mode_indicator = "[●]"
        mode_text = self._mode
        session_text = self._session_name or "New Session"

        # Compose the full header string
        content = f" {header_text}  {mode_indicator} {mode_text}     [Session: {session_text}]"

        # Truncate if needed
        inner_width = cols - 2  # leave room for corners
        if len(content) > inner_width:
            content = content[:inner_width]
        content = content.ljust(inner_width)

        return FormattedText(
            [
                (f"fg:{c['header_border']}", _corner_tl()),
                (f"fg:{c['header_border']}", _hline(len(header_text) + 2)),
                (f"fg:{c['header_border']}", _t_down()),
                (f"fg:{c['header_border']}", _hline(cols - len(header_text) - 4)),
                (f"fg:{c['header_border']}", _corner_tr()),
                ("", "\n"),
                (f"fg:{c['header_border']}", _vline()),
                (f"fg:{c['header_title']} bold", f" {header_text} "),
                (f"fg:{c['header_border']}", _vline()),
                (f"fg:{c['header_text']}", f" {mode_indicator} {mode_text}"),
                (
                    "",
                    " "
                    * max(
                        0,
                        cols
                        - len(header_text)
                        - 2
                        - len(mode_indicator)
                        - 1
                        - len(mode_text)
                        - len(f"[Session: {session_text}]")
                        - 2,
                    ),
                ),
                (f"fg:{c['header_dim']}", f"[Session: {session_text}]"),
                (f"fg:{c['header_border']}", " " + _vline()),
                ("", "\n"),
                (f"fg:{c['header_border']}", _corner_bl()),
                (f"fg:{c['header_border']}", _hline(self._sidebar_width)),
                (f"fg:{c['header_border']}", _t_up()),
                (f"fg:{c['header_border']}", _hline(cols - self._sidebar_width - 2)),
                (f"fg:{c['header_border']}", _corner_br()),
            ]
        )

    def _build_main_body(self) -> FormattedText:
        """Build the main body: left sidebar + right panel."""
        size = self._get_terminal_size()
        cols = size.columns
        lines = size.lines
        c = self._colors

        # Reserve lines: header(3) + focus(2) + input(2) + func_keys(1) = 8
        reserved = 8
        body_lines = max(3, lines - reserved)

        # Split body: activity area takes ~60%, interaction takes ~40%
        activity_lines = max(3, body_lines * 3 // 5)
        interaction_lines = max(2, body_lines - activity_lines - 1)

        sw = self._sidebar_width  # sidebar width

        result_lines = []

        # ── Activity section ──
        # Left sidebar: AGENT FLEET header
        fleet_title = "👥 AGENT FLEET"
        result_lines.append(
            (f"fg:{c['sidebar_border']}", _vline())
            + (f"fg:{c['sidebar_title']} bold", f" {fleet_title}")
            + ("", " " * max(0, sw - len(fleet_title) - 2))
            + (f"fg:{c['sidebar_border']}", _vline())
            + ("", " " * max(0, cols - sw - 1))
            + (f"fg:{c['panel_border']}", _vline())
            + (f"fg:{c['panel_title']} bold", " 🚀 LIVE AGENT ACTIVITY")
            + ("", "\n")
        )

        # Agent fleet rows
        color_map = {
            "yellow": f"fg:{c['status_yellow']}",
            "blue": f"fg:{c['status_blue']}",
            "green": f"fg:{c['status_green']}",
            "white": f"fg:{c['status_white']}",
            "red": f"fg:{c['status_red']}",
        }
        dot_map = {
            "yellow": "🟡",
            "blue": "🔵",
            "green": "🟢",
            "white": "⚪",
            "red": "🔴",
        }

        fleet_lines_used = 0
        for agent in self._agent_fleet:
            name = agent.get("name", "UNKNOWN")
            status = agent.get("status", "")
            color = agent.get("color", "white")
            dot = dot_map.get(color, "⚪")
            fleet_line = f" {dot} {name}"
            if status:
                fleet_line += f"  [{status}]"
            fleet_line = fleet_line.ljust(sw - 1)

            result_lines.append(
                (f"fg:{c['sidebar_border']}", _vline())
                + (f"fg:{c['sidebar_text']}", fleet_line)
                + (f"fg:{c['sidebar_border']}", _vline())
                + ("", " " * max(0, cols - sw - 1))
                + (f"fg:{c['panel_border']}", _vline())
                + ("", "\n")
            )
            fleet_lines_used += 1

        # Fill remaining activity lines with activity info on the right
        activity_info = self._build_activity_info_lines(cols - sw - 1)
        for i in range(activity_lines - 1):
            # Left sidebar: empty or context/tools/tasks
            left_content = self._get_sidebar_line(i, sw)
            right_content = ""
            if i < len(activity_info):
                right_content = activity_info[i]
            else:
                right_content = " " * (cols - sw - 2)

            result_lines.append(
                left_content
                + (f"fg:{c['panel_border']}", _vline())
                + (f"fg:{c['panel_text']}", right_content.ljust(cols - sw - 2))
                + (f"fg:{c['panel_border']}", _vline())
                + ("", "\n")
            )

        # Separator between activity and interaction
        result_lines.append(
            (f"fg:{c['sidebar_border']}", _t_right())
            + (f"fg:{c['sidebar_border']}", _hline(sw - 1))
            + (f"fg:{c['sidebar_border']}", _t_left())
            + (f"fg:{c['panel_border']}", _hline(cols - sw - 1))
            + (f"fg:{c['panel_border']}", _vline())
            + ("", "\n")
        )

        # ── Interaction section ──
        interaction_title = "💬 INTERACTION"
        result_lines.append(
            (f"fg:{c['interaction_border']}", _vline())
            + (f"fg:{c['interaction_title']} bold", f" {interaction_title}")
            + ("", " " * max(0, sw - len(interaction_title) - 2))
            + (f"fg:{c['interaction_border']}", _vline())
            + (f"fg:{c['interaction_border']}", _hline(cols - sw - 1))
            + (f"fg:{c['interaction_border']}", _vline())
            + ("", "\n")
        )

        # Interaction content lines
        interaction_content = self._build_interaction_lines(
            cols - sw - 2, interaction_lines - 1
        )
        for i in range(interaction_lines - 1):
            left_content = self._get_sidebar_line(fleet_lines_used + i, sw)
            right_line = ""
            if i < len(interaction_content):
                right_line = interaction_content[i]
            else:
                right_line = " " * (cols - sw - 2)

            result_lines.append(
                left_content
                + (f"fg:{c['interaction_border']}", _vline())
                + ("", right_line.ljust(cols - sw - 2))
                + (f"fg:{c['interaction_border']}", _vline())
                + ("", "\n")
            )

        return FormattedText(result_lines)

    def _build_activity_info_lines(self, width: int) -> list[str]:
        """Build the LIVE AGENT ACTIVITY info lines."""
        a = self._live_activity
        c = self._colors

        # Progress bar
        progress = min(100, max(0, a.get("progress", 0)))
        bar_width = min(16, max(4, width // 4))
        filled = round((progress / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        lines = []
        items = [
            f"1. 🟦 ACTIVE AGENT  : [ {a.get('agent', '—')} ]",
            f"2. 📋 CURRENT TASK  : [ {a.get('task', '—')} ]",
            f"3. 🛠️  ACTION       : [ {a.get('action', '—')} ]",
            f"4. 📂 LOCATION     : [ {a.get('location', '—')} ]",
            f"5. 📊 STATUS       : [ {bar} ] {progress}%",
        ]
        for item in items:
            lines.append(item[:width].ljust(width))
        return lines

    def _get_sidebar_line(self, line_idx: int, sw: int) -> list:
        """Get a single line of sidebar content for the given line index."""
        c = self._colors
        # Lines 0-4: Agent Fleet (header + agents)
        fleet_count = len(self._agent_fleet)
        if line_idx <= fleet_count:
            return self._get_fleet_line(line_idx, sw, c)

        # After fleet: CONTEXT & TOOLS section
        ctx_start = fleet_count + 1
        if line_idx == ctx_start:
            ctx_title = "🌐 CONTEXT & TOOLS"
            content = f" {ctx_title}"
            return [
                (f"fg:{c['sidebar_border']}", _vline()),
                (f"fg:{c['sidebar_title']} bold", content),
                ("", " " * max(0, sw - len(content) - 2)),
                (f"fg:{c['sidebar_border']}", _vline()),
            ]

        # Memory status
        if line_idx == ctx_start + 1:
            content = f" 🧠 Mem: {self._memory_status}"
            return [
                (f"fg:{c['sidebar_border']}", _vline()),
                (f"fg:{c['sidebar_text']}", content),
                ("", " " * max(0, sw - len(content) - 2)),
                (f"fg:{c['sidebar_border']}", _vline()),
            ]

        # Active tools
        if line_idx == ctx_start + 2:
            content = " 🛠️  Active Tools:"
            return [
                (f"fg:{c['sidebar_border']}", _vline()),
                (f"fg:{c['sidebar_text']}", content),
                ("", " " * max(0, sw - len(content) - 2)),
                (f"fg:{c['sidebar_border']}", _vline()),
            ]

        tool_start = ctx_start + 3
        tool_idx = line_idx - tool_start
        if 0 <= tool_idx < len(self._tools):
            tool = self._tools[tool_idx]
            is_last = tool_idx == len(self._tools) - 1
            prefix = "   └─" if is_last else "   ├─"
            content = f"{prefix} {tool}"
            return [
                (f"fg:{c['sidebar_border']}", _vline()),
                (f"fg:{c['sidebar_dim']}", content),
                ("", " " * max(0, sw - len(content) - 2)),
                (f"fg:{c['sidebar_border']}", _vline()),
            ]

        # After tools: QUICK TASKS section
        tasks_section_start = tool_start + len(self._tools) + 1
        if line_idx == tasks_section_start:
            tasks_title = "📋 QUICK TASKS"
            content = f" {tasks_title}"
            return [
                (f"fg:{c['sidebar_border']}", _vline()),
                (f"fg:{c['sidebar_title']} bold", content),
                ("", " " * max(0, sw - len(content) - 2)),
                (f"fg:{c['sidebar_border']}", _vline()),
            ]

        task_start = tasks_section_start + 1
        task_idx = line_idx - task_start
        if 0 <= task_idx < len(self._tasks):
            task = self._tasks[task_idx]
            check = "x" if task.get("done") else " "
            content = f" [{check}] {task.get('id', '')} {task.get('label', '')}"
            return [
                (f"fg:{c['sidebar_border']}", _vline()),
                (f"fg:{c['sidebar_text']}", content),
                ("", " " * max(0, sw - len(content) - 2)),
                (f"fg:{c['sidebar_border']}", _vline()),
            ]

        # Empty sidebar line
        return [
            (f"fg:{c['sidebar_border']}", _vline()),
            ("", " " * (sw - 1)),
            (f"fg:{c['sidebar_border']}", _vline()),
        ]

    def _get_fleet_line(self, line_idx: int, sw: int, c: dict) -> list:
        """Build a fleet line (header or agent row)."""
        if line_idx == 0:
            # Already handled in _build_main_body header
            return [
                (f"fg:{c['sidebar_border']}", _vline()),
                ("", " " * (sw - 1)),
                (f"fg:{c['sidebar_border']}", _vline()),
            ]

        agent_idx = line_idx - 1
        if agent_idx < len(self._agent_fleet):
            agent = self._agent_fleet[agent_idx]
            name = agent.get("name", "UNKNOWN")
            status = agent.get("status", "")
            color = agent.get("color", "white")
            dot_map = {
                "yellow": "🟡",
                "blue": "🔵",
                "green": "🟢",
                "white": "⚪",
                "red": "🔴",
            }
            dot = dot_map.get(color, "⚪")
            fleet_line = f" {dot} {name}"
            if status:
                fleet_line += f"  [{status}]"
            fleet_line = fleet_line.ljust(sw - 1)
            return [
                (f"fg:{c['sidebar_border']}", _vline()),
                (f"fg:{c['sidebar_text']}", fleet_line),
                (f"fg:{c['sidebar_border']}", _vline()),
            ]

        return [
            (f"fg:{c['sidebar_border']}", _vline()),
            ("", " " * (sw - 1)),
            (f"fg:{c['sidebar_border']}", _vline()),
        ]

    def _build_interaction_lines(self, width: int, max_lines: int) -> list[str]:
        """Build the interaction/chat content lines."""
        if not self._interactions:
            return [" " * width] * max_lines

        lines = []
        for msg in self._interactions[-max_lines:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # Truncate long content
            if len(content) > width - 12:
                content = content[: width - 15] + "..."
            role_label = role.upper()
            line = f"  {role_label}: {content}"
            lines.append(line[:width].ljust(width))

        # Pad if needed
        while len(lines) < max_lines:
            lines.append(" " * width)

        return lines[-max_lines:]

    def _build_focus_line(self) -> FormattedText:
        """Build the focus/status line."""
        cols = self._get_terminal_size().columns
        c = self._colors

        focus_text = self._focus_text or "Ready"
        content = f" ⚡ FOCUS: [ {focus_text} ]"

        # Truncate/pad
        inner = cols - 2
        if len(content) > inner:
            content = content[:inner]
        content = content.ljust(inner)

        return FormattedText(
            [
                (f"fg:{c['focus_border']}", _corner_bl()),
                (f"fg:{c['focus_border']}", _hline(inner)),
                (f"fg:{c['focus_border']}", _corner_br()),
                ("", "\n"),
                (f"fg:{c['focus_border']}", _vline()),
                (f"fg:{c['focus_text']} bold", content),
                (f"fg:{c['focus_border']}", _vline()),
            ]
        )

    def _build_func_key_bar(self) -> FormattedText:
        """Build the function key bar at the bottom."""
        cols = self._get_terminal_size().columns
        c = self._colors

        parts = []
        for key, label in self._function_keys:
            parts.append(f"[{key}] {label}")
        content = "  " + "  ".join(parts)

        # Truncate/pad
        if len(content) > cols:
            content = content[:cols]
        content = content.ljust(cols)

        return FormattedText(
            [
                (f"fg:{c['func_key_dim']}", content),
            ]
        )

    # ── prompt_toolkit layout ────────────────────────────────────────────────

    def _build_layout(self):
        """Build the full prompt_toolkit layout."""
        kb = KeyBindings()

        # Build the input area
        input_area = TextArea(
            height=Dimension(min=1, max=3, preferred=1),
            prompt=[("class:dashboard-input-prompt", " ⌨️ INPUT: ")],
            style="class:dashboard-input-area",
            multiline=False,
            wrap_lines=False,
            history=None,  # Use parent's history
        )

        # Keybindings
        @kb.add("enter")
        def _(event):
            text = event.app.current_buffer.text.strip()
            if text:
                event.app.current_buffer.reset(append_to_history=True)
                # Submit via callback
                if hasattr(self, "_on_submit"):
                    self._on_submit(text)

        @kb.add("c-c")
        def _(event):
            if hasattr(self, "_on_interrupt"):
                self._on_interrupt()
            else:
                self.stop()

        @kb.add("c-d")
        def _(event):
            self.stop()

        @kb.add("escape", "enter")
        def _(event):
            event.current_buffer.insert_text("\n")

        @kb.add("c-j")
        def _(event):
            event.current_buffer.insert_text("\n")

        @kb.add("tab")
        def _(event):
            buf = event.current_buffer
            if buf.complete_state:
                completion = buf.complete_state.current_completion
                if completion:
                    buf.apply_completion(completion)
            else:
                buf.start_completion()

        # Build the main content as a FormattedTextControl that re-renders
        def _get_main_content():
            return self._build_main_body()

        def _get_focus_content():
            return self._build_focus_line()

        def _get_func_key_content():
            return self._build_func_key_bar()

        main_window = Window(
            content=FormattedTextControl(_get_main_content),
            wrap_lines=True,
        )

        focus_window = Window(
            content=FormattedTextControl(_get_focus_content),
            height=1,
        )

        func_key_window = Window(
            content=FormattedTextControl(_get_func_key_content),
            height=1,
        )

        layout = Layout(
            HSplit(
                [
                    main_window,
                    focus_window,
                    Window(char="─", height=1, style="class:dashboard-input-rule"),
                    input_area,
                    func_key_window,
                ]
            )
        )

        return layout, kb, input_area

    def _build_style(self):
        """Build the prompt_toolkit style dict."""
        c = self._colors
        return {
            "dashboard-input-prompt": f"fg:{c['input_prompt']} bold",
            "dashboard-input-area": f"fg:{c['input_text']}",
            "dashboard-input-rule": f"fg:{c['input_border']}",
            "completion-menu": c.get("completion_menu", "bg:#1a1a2e #FFF8DC"),
            "completion-menu.completion.current": c.get(
                "completion_menu_current", "bg:#333355 #FFD700"
            ),
        }

    def start(self, on_submit=None, on_interrupt=None):
        """Start the dashboard event loop.

        Args:
            on_submit: Callback(text: str) called when user submits input.
            on_interrupt: Callback() called on Ctrl+C.
        """
        self._on_submit = on_submit
        self._on_interrupt = on_interrupt

        layout, kb, input_area = self._build_layout()
        style_dict = self._build_style()

        from prompt_toolkit.styles import Style as PTStyle

        try:
            from prompt_toolkit.cursor_shapes import CursorShape

            cursor = CursorShape.BLOCK
        except (ImportError, AttributeError):
            cursor = None

        style = PTStyle.from_dict(style_dict)

        app = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=True,
            mouse_support=False,
            **({"cursor": cursor} if cursor else {}),
        )

        self._app = app

        # Refresh loop
        import threading

        def refresh_loop():
            while not self._should_exit:
                if self._app:
                    self._invalidate(min_interval=0.5)
                time.sleep(0.5)

        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()

        try:
            app.run()
        except (EOFError, KeyboardInterrupt):
            pass
        finally:
            self._should_exit = True
