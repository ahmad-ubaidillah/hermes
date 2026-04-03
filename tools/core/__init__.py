# Tools Core - Re-export from subfolders for backward compatibility

# Web tools (moved to tools/web/)
try:
    from tools.web.web_tools import (
        web_search_tool,
        web_extract_tool,
        web_crawl_tool,
        check_firecrawl_api_key,
    )
except ImportError:
    pass

# Terminal tools (moved to tools/terminal/)
try:
    from tools.terminal.terminal_tool import (
        terminal_tool,
        check_terminal_requirements,
        cleanup_vm,
        cleanup_all_environments,
        get_active_environments_info,
        register_task_env_overrides,
        clear_task_env_overrides,
        TERMINAL_TOOL_DESCRIPTION,
    )
except ImportError:
    pass

# Vision tools (moved to tools/web/)
try:
    from tools.web.vision_tools import (
        vision_analyze_tool,
        check_vision_requirements,
    )
except ImportError:
    pass

# Browser tools (moved to tools/web/)
try:
    from tools.web.browser_tool import (
        browser_navigate,
        browser_snapshot,
        browser_click,
        browser_type,
        browser_scroll,
        browser_back,
        browser_press,
        browser_close,
        browser_get_images,
        browser_vision,
        cleanup_browser,
        cleanup_all_browsers,
        get_active_browser_sessions,
        check_browser_requirements,
        BROWSER_TOOL_SCHEMAS,
    )
except ImportError:
    pass

__all__ = [
    "web_search_tool",
    "web_extract_tool",
    "web_crawl_tool",
    "check_firecrawl_api_key",
    "terminal_tool",
    "check_terminal_requirements",
    "vision_analyze_tool",
    "check_vision_requirements",
    "browser_navigate",
    "browser_snapshot",
    "check_browser_requirements",
    "BROWSER_TOOL_SCHEMAS",
]
