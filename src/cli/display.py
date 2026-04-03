"""Display helpers for CLI."""

from typing import Any


def _accent_hex() -> str:
    """Return the active skin accent color for legacy CLI output lines."""
    try:
        from aizen_cli.skin_engine import get_active_skin

        return get_active_skin().get_color("ui_accent", "#FFBF00")
    except Exception:
        return "#FFBF00"


def _rich_text_from_ansi(text: str) -> Any:
    """Safely render assistant/tool output that may contain ANSI escapes."""
    try:
        from rich.text import Text

        return Text.from_ansi(text)
    except Exception:
        return text


def _cprint(text: str):
    """Print ANSI-colored text through prompt_toolkit's native renderer."""
    try:
        from prompt_toolkit import print_formatted_text as _pt_print
        from prompt_toolkit.formatted_text import ANSI as _PT_ANSI

        _pt_print(_PT_ANSI(text))
    except Exception:
        print(text)


def _build_compact_banner() -> str:
    """Build compact banner for CLI."""
    try:
        from aizen_cli.banner import build_banner

        return build_banner()
    except Exception:
        return "Aizen Agent"
