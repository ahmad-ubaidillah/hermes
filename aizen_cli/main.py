     1|#!/usr/bin/env python3
     2|"""
     3|Aizen CLI - Main entry point.
     4|
     5|Usage:
     6|    aizen                     # Interactive chat (default)
     7|    aizen chat                # Interactive chat
     8|    aizen gateway             # Run gateway in foreground
     9|    aizen gateway start       # Start gateway as service
    10|    aizen gateway stop        # Stop gateway service
    11|    aizen gateway status      # Show gateway status
    12|    aizen gateway install     # Install gateway service
    13|    aizen gateway uninstall   # Uninstall gateway service
    14|    aizen setup               # Interactive setup wizard
    15|    aizen logout              # Clear stored authentication
    16|    aizen status              # Show status of all components
    17|    aizen cron                # Manage cron jobs
    18|    aizen cron list           # List cron jobs
    19|    aizen cron status         # Check if cron scheduler is running
    20|    aizen doctor              # Check configuration and dependencies
    37|    aizen version             Show version
    38|    aizen update              Update to latest version
    39|    aizen uninstall           Uninstall Aizen Agent
    40|    aizen acp                 Run as an ACP server for editor integration
    41|    aizen sessions browse     Interactive session picker with search
    42|
    43|    aizen claw migrate --dry-run  # Preview migration without changes
    44|"""
    45|
    46|import argparse
    47|import os
    48|import subprocess
    49|import sys
    50|from pathlib import Path
    51|from typing import Optional
    52|
    53|def _require_tty(command_name: str) -> None:
    54|    """Exit with a clear error if stdin is not a terminal.
    55|
    56|    Interactive TUI commands (aizen tools, aizen setup, aizen model) use
    57|    curses or input() prompts that spin at 100% CPU when stdin is a pipe.
    58|    This guard prevents accidental non-interactive invocation.
    59|    """
    60|    if not sys.stdin.isatty():
    61|        print(
    62|            f"Error: 'aizen {command_name}' requires an interactive terminal.\n"
    63|            f"It cannot be run through a pipe or non-interactive subprocess.\n"
    64|            f"Run it directly in your terminal instead.",
    65|            file=sys.stderr,
    66|        )
    67|        sys.exit(1)
    68|
    69|
    70|# Add project root to path
    71|PROJECT_ROOT = Path(__file__).parent.parent.resolve()
    72|sys.path.insert(0, str(PROJECT_ROOT))
    73|
    74|# ---------------------------------------------------------------------------
    75|# Profile override — MUST happen before any aizen module import.
    76|#
    77|# Many modules cache AIZEN_HOME at import time (module-level constants).
    78|# We intercept --profile/-p from sys.argv here and set the env var so that
    79|# every subsequent ``os.getenv("AIZEN_HOME", ...)`` resolves correctly.
    80|# The flag is stripped from sys.argv so argparse never sees it.
    81|# Falls back to ~/.aizen/active_profile for sticky default.
    82|# ---------------------------------------------------------------------------
    83|def _apply_profile_override() -> None:
    84|    """Pre-parse --profile/-p and set AIZEN_HOME before module imports."""
    85|    argv = sys.argv[1:]
    86|    profile_name = None
    87|    consume = 0
    88|
    89|    # 1. Check for explicit -p / --profile flag
    90|    for i, arg in enumerate(argv):
    91|        if arg in ("--profile", "-p") and i + 1 < len(argv):
    92|            profile_name = argv[i + 1]
    93|            consume = 2
    94|            break
    95|        elif arg.startswith("--profile="):
    96|            profile_name = arg.split("=", 1)[1]
    97|            consume = 1
    98|            break
    99|
   100|    # 2. If no flag, check ~/.aizen/active_profile
   101|    if profile_name is None:
   102|        try:
   103|            active_path = Path.home() / ".aizen" / "active_profile"
   104|            if active_path.exists():
   105|                name = active_path.read_text().strip()
   106|                if name and name != "default":
   107|                    profile_name = name
   108|                    consume = 0  # don't strip anything from argv
   109|        except (UnicodeDecodeError, OSError):
   110|            pass  # corrupted file, skip
   111|
   112|    # 3. If we found a profile, resolve and set AIZEN_HOME
   113|    if profile_name is not None:
   114|        try:
   115|            from aizen_cli.profiles import resolve_profile_env
   116|            aizen_home = resolve_profile_env(profile_name)
   117|        except (ValueError, FileNotFoundError) as exc:
   118|            print(f"Error: {exc}", file=sys.stderr)
   119|            sys.exit(1)
   120|        except Exception as exc:
   121|            # A bug in profiles.py must NEVER prevent aizen from starting
   122|            print(f"Warning: profile override failed ({exc}), using default", file=sys.stderr)
   123|            return
   124|        os.environ["AIZEN_HOME"] = aizen_home
   125|        # Strip the flag from argv so argparse doesn't choke
   126|        if consume > 0:
   127|            for i, arg in enumerate(argv):
   128|                if arg in ("--profile", "-p"):
   129|                    start = i + 1  # +1 because argv is sys.argv[1:]
   130|                    sys.argv = sys.argv[:start] + sys.argv[start + consume:]
   131|                    break
   132|                elif arg.startswith("--profile="):
   133|                    start = i + 1
   134|                    sys.argv = sys.argv[:start] + sys.argv[start + 1:]
   135|                    break
   136|
   137|_apply_profile_override()
   138|
   139|# Load .env from ~/.aizen/.env first, then project root as dev fallback.
   140|# User-managed env files should override stale shell exports on restart.
   141|from aizen_cli.config import get_aizen_home
   142|from aizen_cli.env_loader import load_aizen_dotenv
   143|load_aizen_dotenv(project_env=PROJECT_ROOT / '.env')
   144|
   145|
   146|import logging
   147|import time as _time
   148|from datetime import datetime
   149|
   150|from aizen_cli import __version__, __release_date__
   151|from core.aizen_constants import OPENROUTER_BASE_URL
   152|
   153|logger = logging.getLogger(__name__)
   154|
   155|
   156|def _relative_time(ts) -> str:
   157|    """Format a timestamp as relative time (e.g., '2h ago', 'yesterday')."""
   158|    if not ts:
   159|        return "?"
   160|    delta = _time.time() - ts
   161|    if delta < 60:
   162|        return "just now"
   163|    if delta < 3600:
   164|        return f"{int(delta / 60)}m ago"
   165|    if delta < 86400:
   166|        return f"{int(delta / 3600)}h ago"
   167|    if delta < 172800:
   168|        return "yesterday"
   169|    if delta < 604800:
   170|        return f"{int(delta / 86400)}d ago"
   171|    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
   172|
   173|
   174|def _has_any_provider_configured() -> bool:
   175|    """Check if at least one inference provider is usable."""
   176|    from aizen_cli.config import get_env_path, get_aizen_home
   177|    from aizen_cli.auth import get_auth_status
   178|
   179|    # Check env vars (may be set by .env or shell).
   180|    # OPENAI_BASE_URL alone counts — local models (vLLM, llama.cpp, etc.)
   181|    # often don't require an API key.
   182|    from aizen_cli.auth import PROVIDER_REGISTRY
   183|
   184|    # Collect all provider env vars
   185|    provider_env_vars = {"OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN", "OPENAI_BASE_URL"}
   186|    for pconfig in PROVIDER_REGISTRY.values():
   187|        if pconfig.auth_type=*** "api_key":
   188|            provider_env_vars.update(pconfig.api_key_env_vars)
   189|    if any(os.getenv(v) for v in provider_env_vars):
   190|        return True
   191|
   192|    # Check .env file for keys
   193|    env_file = get_env_path()
   194|    if env_file.exists():
   195|        try:
   196|            for line in env_file.read_text().splitlines():
   197|                line = line.strip()
   198|                if line.startswith("#") or "=" not in line:
   199|                    continue
   200|                key, _, val = line.partition("=")
   201|                val = val.strip().strip("'\"")
   202|                if key.strip() in provider_env_vars and val:
   203|                    return True
   204|        except Exception:
   205|            pass
   206|
   207|    # Check provider-specific auth fallbacks (for example, Copilot via gh auth).
   208|    try:
   209|        for provider_id, pconfig in PROVIDER_REGISTRY.items():
   210|            if pconfig.auth_type != "api_key":
   211|                continue
   212|            status = get_auth_status(provider_id)
   213|            if status.get("logged_in"):
   214|                return True
   215|    except Exception:
   216|        pass
   217|
   218|    # Check for Nous Portal OAuth credentials
   219|    auth_file=*** / "auth.json"
   220|    if auth_file.exists():
   221|        try:
   222|            import json
   223|            auth=json.l...t())
   224|            active = auth.get("active_provider")
   225|            if active:
   226|                status = get_auth_status(active)
   227|                if status.get("logged_in"):
   228|                    return True
   229|        except Exception:
   230|            pass
   231|
   232|
   233|    # Check for Claude Code OAuth credentials (~/.claude/.credentials.json)
   234|    # These are used by resolve_anthropic_token() at runtime but were missing
   235|    # from this startup gate check.
   236|    try:
   237|        from agent.anthropic_adapter import read_claude_code_credentials, is_claude_code_token_valid
   238|        creds = read_claude_code_credentials()
   239|        if creds and (is_claude_code_token_valid(creds) or creds.get("refreshToken")):
   240|            return True
   241|    except Exception:
   242|        pass
   243|
   244|    return False
   245|
   246|
   247|def _session_browse_picker(sessions: list) -> Optional[str]:
   248|    """Interactive curses-based session browser with live search filtering.
   249|
   250|    Returns the selected session ID, or None if cancelled.
   251|    Uses curses (not simple_term_menu) to avoid the ghost-duplication rendering
   252|    bug in tmux/iTerm when arrow keys are used.
   253|    """
   254|    if not sessions:
   255|        print("No sessions found.")
   256|        return None
   257|
   258|    # Try curses-based picker first
   259|    try:
   260|        import curses
   261|
   262|        result_holder = [None]
   263|
   264|        def _format_row(s, max_x):
   265|            """Format a session row for display."""
   266|            title = (s.get("title") or "").strip()
   267|            preview = (s.get("preview") or "").strip()
   268|            source = s.get("source", "")[:6]
   269|            last_active = _relative_time(s.get("last_active"))
   270|            sid = s["id"][:18]
   271|
   272|            # Adaptive column widths based on terminal width
   273|            # Layout: [arrow 3] [title/preview flexible] [active 12] [src 6] [id 18]
   274|            fixed_cols = 3 + 12 + 6 + 18 + 6  # arrow + active + src + id + padding
   275|            name_width = max(20, max_x - fixed_cols)
   276|
   277|            if title:
   278|                name = title[:name_width]
   279|            elif preview:
   280|                name = preview[:name_width]
   281|            else:
   282|                name = sid
   283|
   284|            return f"{name:<{name_width}}  {last_active:<10}  {source:<5} {sid}"
   285|
   286|        def _match(s, query):
   287|            """Check if a session matches the search query (case-insensitive)."""
   288|            q = query.lower()
   289|            return (
   290|                q in (s.get("title") or "").lower()
   291|                or q in (s.get("preview") or "").lower()
   292|                or q in s.get("id", "").lower()
   293|                or q in (s.get("source") or "").lower()
   294|            )
   295|
   296|        def _curses_browse(stdscr):
   297|            curses.curs_set(0)
   298|            if curses.has_colors():
   299|                curses.start_color()
   300|                curses.use_default_colors()
   301|                curses.init_pair(1, curses.COLOR_GREEN, -1)   # selected
   302|                curses.init_pair(2, curses.COLOR_YELLOW, -1)  # header
   303|                curses.init_pair(3, curses.COLOR_CYAN, -1)    # search
   304|                curses.init_pair(4, 8, -1)                    # dim
   305|
   306|            cursor = 0
   307|            scroll_offset = 0
   308|            search_text = ""
   309|            filtered = list(sessions)
   310|
   311|            while True:
   312|                stdscr.clear()
   313|                max_y, max_x = stdscr.getmaxyx()
   314|                if max_y < 5 or max_x < 40:
   315|                    # Terminal too small
   316|                    try:
   317|                        stdscr.addstr(0, 0, "Terminal too small")
   318|                    except curses.error:
   319|                        pass
   320|                    stdscr.refresh()
   321|                    stdscr.getch()
   322|                    return
   323|
   324|                # Header line
   325|                if search_text:
   326|                    header = f"  Browse sessions — filter: {search_text}█"
   327|                    header_attr = curses.A_BOLD
   328|                    if curses.has_colors():
   329|                        header_attr |= curses.color_pair(3)
   330|                else:
   331|                    header = "  Browse sessions — ↑↓ navigate  Enter select  Type to filter  Esc quit"
   332|                    header_attr = curses.A_BOLD
   333|                    if curses.has_colors():
   334|                        header_attr |= curses.color_pair(2)
   335|                try:
   336|                    stdscr.addnstr(0, 0, header, max_x - 1, header_attr)
   337|                except curses.error:
   338|                    pass
   339|
   340|                # Column header line
   341|                fixed_cols = 3 + 12 + 6 + 18 + 6
   342|                name_width = max(20, max_x - fixed_cols)
   343|                col_header = f"   {'Title / Preview':<{name_width}}  {'Active':<10}  {'Src':<5} {'ID'}"
   344|                try:
   345|                    dim_attr = curses.color_pair(4) if curses.has_colors() else curses.A_DIM
   346|                    stdscr.addnstr(1, 0, col_header, max_x - 1, dim_attr)
   347|                except curses.error:
   348|                    pass
   349|
   350|                # Compute visible area
   351|                visible_rows = max_y - 4  # header + col header + blank + footer
   352|                if visible_rows < 1:
   353|                    visible_rows = 1
   354|
   355|                # Clamp cursor and scroll
   356|                if not filtered:
   357|                    try:
   358|                        msg = "  No sessions match the filter."
   359|                        stdscr.addnstr(3, 0, msg, max_x - 1, curses.A_DIM)
   360|                    except curses.error:
   361|                        pass
   362|                else:
   363|                    if cursor >= len(filtered):
   364|                        cursor = len(filtered) - 1
   365|                    if cursor < 0:
   366|                        cursor = 0
   367|                    if cursor < scroll_offset:
   368|                        scroll_offset = cursor
   369|                    elif cursor >= scroll_offset + visible_rows:
   370|                        scroll_offset = cursor - visible_rows + 1
   371|
   372|                    for draw_i, i in enumerate(range(
   373|                        scroll_offset,
   374|                        min(len(filtered), scroll_offset + visible_rows)
   375|                    )):
   376|                        y = draw_i + 3
   377|                        if y >= max_y - 1:
   378|                            break
   379|                        s = filtered[i]
   380|                        arrow = " → " if i == cursor else "   "
   381|                        row = arrow + _format_row(s, max_x - 3)
   382|                        attr = curses.A_NORMAL
   383|                        if i == cursor:
   384|                            attr = curses.A_BOLD
   385|                            if curses.has_colors():
   386|                                attr |= curses.color_pair(1)
   387|                        try:
   388|                            stdscr.addnstr(y, 0, row, max_x - 1, attr)
   389|                        except curses.error:
   390|                            pass
   391|
   392|                # Footer
   393|                footer_y = max_y - 1
   394|                if filtered:
   395|                    footer = f"  {cursor + 1}/{len(filtered)} sessions"
   396|                    if len(filtered) < len(sessions):
   397|                        footer += f" (filtered from {len(sessions)})"
   398|                else:
   399|                    footer = f"  0/{len(sessions)} sessions"
   400|                try:
   401|                    stdscr.addnstr(footer_y, 0, footer, max_x - 1,
   402|                                   curses.color_pair(4) if curses.has_colors() else curses.A_DIM)
   403|                except curses.error:
   404|                    pass
   405|
   406|                stdscr.refresh()
   407|                key = stdscr.getch()
   408|
   409|                if key in (curses.KEY_UP, ):
   410|                    if filtered:
   411|                        cursor = (cursor - 1) % len(filtered)
   412|                elif key in (curses.KEY_DOWN, ):
   413|                    if filtered:
   414|                        cursor = (cursor + 1) % len(filtered)
   415|                elif key in (curses.KEY_ENTER, 10, 13):
   416|                    if filtered:
   417|                        result_holder[0] = filtered[cursor]["id"]
   418|                    return
   419|                elif key == 27:  # Esc
   420|                    if search_text:
   421|                        # First Esc clears the search
   422|                        search_text = ""
   423|                        filtered = list(sessions)
   424|                        cursor = 0
   425|                        scroll_offset = 0
   426|                    else:
   427|                        # Second Esc exits
   428|                        return
   429|                elif key in (curses.KEY_BACKSPACE, 127, 8):
   430|                    if search_text:
   431|                        search_text = search_text[:-1]
   432|                        if search_text:
   433|                            filtered = [s for s in sessions if _match(s, search_text)]
   434|                        else:
   435|                            filtered = list(sessions)
   436|                        cursor = 0
   437|                        scroll_offset = 0
   438|                elif key == ord('q') and not search_text:
   439|                    return
   440|                elif 32 <= key <= 126:
   441|                    # Printable character → add to search filter
   442|                    search_text += chr(key)
   443|                    filtered = [s for s in sessions if _match(s, search_text)]
   444|                    cursor = 0
   445|                    scroll_offset = 0
   446|
   447|        curses.wrapper(_curses_browse)
   448|        return result_holder[0]
   449|
   450|    except Exception:
   451|        pass
   452|
   453|    # Fallback: numbered list (Windows without curses, etc.)
   454|    print("\n  Browse sessions  (enter number to resume, q to cancel)\n")
   455|    for i, s in enumerate(sessions):
   456|        title = (s.get("title") or "").strip()
   457|        preview = (s.get("preview") or "").strip()
   458|        label = title or preview or s["id"]
   459|        if len(label) > 50:
   460|            label = label[:47] + "..."
   461|        last_active = _relative_time(s.get("last_active"))
   462|        src = s.get("source", "")[:6]
   463|        print(f"  {i + 1:>3}. {label:<50}  {last_active:<10}  {src}")
   464|
   465|    while True:
   466|        try:
   467|            val = input(f"\n  Select [1-{len(sessions)}]: ").strip()
   468|            if not val or val.lower() in ("q", "quit", "exit"):
   469|                return None
   470|            idx = int(val) - 1
   471|            if 0 <= idx < len(sessions):
   472|                return sessions[idx]["id"]
   473|            print(f"  Invalid selection. Enter 1-{len(sessions)} or q to cancel.")
   474|        except ValueError:
   475|            print("  Invalid input. Enter a number or q to cancel.")
   476|        except (KeyboardInterrupt, EOFError):
   477|            print()
   478|            return None
   479|
   480|
   481|def _resolve_last_cli_session() -> Optional[str]:
   482|    """Look up the most recent CLI session ID from SQLite. Returns None if unavailable."""
   483|    try:
   484|        from core.aizen_state import SessionDB
   485|        db = SessionDB()
   486|        sessions = db.search_sessions(source="cli", limit=1)
   487|        db.close()
   488|        if sessions:
   489|            return sessions[0]["id"]
   490|    except Exception:
   491|        pass
   492|    return None
   493|
   494|
   495|def _resolve_session_by_name_or_id(name_or_id: str) -> Optional[str]:
   496|    """Resolve a session name (title) or ID to a session ID.
   497|
   498|    - If it looks like a session ID (contains underscore + hex), try direct lookup first.
   499|    - Otherwise, treat it as a title and use resolve_session_by_title (auto-latest).
   500|    - Falls back to the other method if the first doesn't match.
   501|