"""ChatConsole class - Rich Console adapter for prompt_toolkit."""

from typing import Any, Optional


class ChatConsole:
    """Rich Console adapter for prompt_toolkit's patch_stdout context.

    Captures Rich's rendered ANSI output and routes it through _cprint
    so colors and markup render correctly inside the interactive chat loop.
    """

    def __init__(self, **kwargs):
        self._output = []

    def print(self, *args, **kwargs):
        """Print to console."""
        pass

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access."""
        return lambda *a, **kw: None
