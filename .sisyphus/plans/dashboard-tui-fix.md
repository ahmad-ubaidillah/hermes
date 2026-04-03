# Dashboard TUI Fix Plan

## Goal
Fix all identified issues in `aizen_cli/dashboard_tui.py` to make it production-ready with proper resize handling, multiline input, history, completions, error handling, and dynamic data wiring.

## Scope
**IN**: `aizen_cli/dashboard_tui.py` only — no changes to `cli.py` or other files
**OUT**: No new features beyond what's needed to match classic TUI parity
**Approach**: Fix all issues in-place, keep existing API surface intact

---

## Task 1: Fix Terminal Resize & Responsive Layout

**Problem**: `_get_terminal_size()` uses `shutil.get_terminal_size()` which is static. Layout doesn't adapt to window resize. Sidebar width is hardcoded to 24.

**Changes**:
1. Add `@property _effective_sidebar_width` that computes proportional width:
   ```python
   @property
   def _effective_sidebar_width(self):
       cols = self._get_terminal_size().columns
       return min(28, max(18, cols // 4))
   ```
2. Replace all `self._sidebar_width` references with `self._effective_sidebar_width`
3. Remove `_sidebar_width` from `__init__`
4. In `_build_main_body()`, compute `sw = self._effective_sidebar_width` at top of method
5. In `_build_focus_line()` and `_build_func_key_bar()`, use `cols - 2` for inner width (already done, but verify)

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 2: Fix Unicode/Emoji Width Calculation

**Problem**: String truncation uses `len()` which counts emoji as 1 char but they render as 2 cells. This causes layout overflow on terminals.

**Changes**:
1. Add import: `from prompt_toolkit.utils import get_cwidth`
2. Add helper method:
   ```python
   def _visible_len(self, text: str) -> int:
       """Return display width accounting for wide characters."""
       return get_cwidth(text)
   ```
3. In `_build_activity_info_lines()`, replace `item[:width]` with a width-aware truncation:
   ```python
   def _truncate_to_width(self, text: str, max_width: int) -> str:
       result = ""
       for ch in text:
           if get_cwidth(result + ch) > max_width:
               break
           result += ch
       return result
   ```
4. Apply `_truncate_to_width()` in all places that truncate content to fit panel width

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 3: Fix Input — Multiline, History, Completions, Read-Only

**Problem**: Dashboard input is single-line, no history, no slash-command completions, no read-only state.

**Changes**:
1. In `_build_layout()`, update `TextArea` constructor:
   ```python
   input_area = TextArea(
       height=Dimension(min=1, max=4, preferred=1),
       prompt=[("class:dashboard-input-prompt", " ⌨️ INPUT: ")],
       style="class:dashboard-input-area",
       multiline=True,
       wrap_lines=True,
       read_only=Condition(lambda: getattr(self, "_command_running", False)),
       history=FileHistory(str(self._cli._history_file)) if hasattr(self._cli, "_history_file") else None,
       completer=SlashCommandCompleter(
           skill_commands_provider=lambda: getattr(self._cli, "_skill_commands", []),
       ),
       complete_while_typing=True,
       auto_suggest=SlashCommandAutoSuggest(
           history_suggest=AutoSuggestFromHistory(),
           completer=SlashCommandCompleter(
               skill_commands_provider=lambda: getattr(self._cli, "_skill_commands", []),
           ),
       ),
   )
   ```
2. Add imports at top:
   ```python
   from prompt_toolkit.history import FileHistory
   from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
   ```
3. Add `Alt+Enter` and `Ctrl+J` keybindings for newline insertion (already present, verify they work with multiline)
4. Add dynamic height calculation similar to classic TUI's `_input_height()`:
   ```python
   def _input_height():
       try:
           doc = input_area.buffer.document
           sw = self._effective_sidebar_width
           cols = self._get_terminal_size().columns
           right_width = cols - sw - 2
           prompt_chars = len(" ⌨️ INPUT: ")
           available = max(10, right_width - prompt_chars)
           visual_lines = 0
           for line in doc.lines:
               visual_lines += max(1, -(-len(line) // available))
           return min(max(visual_lines, 1), 4)
       except Exception:
           return 1
   input_area.window.height = _input_height
   ```

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 4: Add Paste Detection & Collapse

**Problem**: No paste detection — large pastes will overflow the input area.

**Changes**:
1. Add paste counter and state as instance variables in `__init__`:
   ```python
   self._paste_counter = 0
   self._prev_text_len = 0
   self._prev_newline_count = 0
   self._paste_just_collapsed = False
   ```
2. Add `_on_text_changed` handler to `input_area.buffer.on_text_changed`:
   ```python
   def _on_text_changed(buf):
       text = buf.text
       chars_added = len(text) - self._prev_text_len
       self._prev_text_len = len(text)
       if self._paste_just_collapsed:
           self._paste_just_collapsed = False
           self._prev_newline_count = text.count('\n')
           return
       line_count = text.count('\n')
       newlines_added = line_count - self._prev_newline_count
       self._prev_newline_count = line_count
       is_paste = chars_added > 1 or newlines_added >= 4
       if line_count >= 5 and is_paste and not text.startswith('/'):
           self._paste_counter += 1
           paste_dir = get_aizen_home() / "pastes"
           paste_dir.mkdir(parents=True, exist_ok=True)
           paste_file = paste_dir / f"paste_{self._paste_counter}_{datetime.now().strftime('%H%M%S')}.txt"
           paste_file.write_text(text, encoding="utf-8")
           self._paste_just_collapsed = True
           buf.text = f"[Pasted text #{self._paste_counter}: {line_count + 1} lines → {paste_file}]"
           buf.cursor_position = len(buf.text)
   ```
3. Add import: `from core.aizen_constants import get_aizen_home`

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 5: Remove Hardcoded Demo Data, Wire Real Data

**Problem**: `__init__` has hardcoded demo data for agent fleet, live activity, tasks, tools. These should default to empty/derived from `cli_ref`.

**Changes**:
1. In `__init__`, replace hardcoded data with defaults derived from `cli_ref`:
   ```python
   # Agent fleet — default empty, populated by update_agent_fleet()
   self._agent_fleet = []

   # Live activity — derive from CLI state
   self._live_activity = {
       "agent": "Aizen",
       "task": "—",
       "action": "Idle",
       "location": os.getcwd(),
       "progress": 0,
   }

   # Interactions — seed from conversation history
   self._interactions = []
   self._seed_interactions_from_history()

   # Tools — derive from enabled_toolsets
   self._tools = []
   self._seed_tools_from_cli()

   # Tasks — derive from todo store if available
   self._tasks = []
   self._seed_tasks_from_cli()

   # Memory status
   self._memory_status = "Active" if self._cli.agent else "Inactive"
   ```
2. Add helper methods:
   ```python
   def _seed_interactions_from_history(self):
       """Load recent conversation history into interactions."""
       for msg in self._cli.conversation_history[-20:]:
           role = msg.get("role", "unknown")
           content = msg.get("content", "")
           if role in ("user", "assistant"):
               text = str(content)[:200] if content else ""
               if text:
                   self._interactions.append({"role": role, "content": text})

   def _seed_tools_from_cli(self):
       """Load enabled toolsets into tools list."""
       toolsets = getattr(self._cli, "enabled_toolsets", []) or []
       self._tools = [t.capitalize().replace("_", " ") for t in toolsets[:5]]

   def _seed_tasks_from_cli(self):
       """Load todos from agent's todo store."""
       agent = getattr(self._cli, "agent", None)
       if agent and hasattr(agent, "_todo_store") and agent._todo_store:
           try:
               todos = agent._todo_store.list_todos()
               self._tasks = [
                   {"id": f"#{i+1:02d}", "label": t.get("content", "")[:20],
                    "done": t.get("status") == "completed"}
                   for i, t in enumerate(todos[:6])
               ]
           except Exception:
               pass
   ```
3. Add import: `import os` (already present via shutil)

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 6: Fix Performance — Replace Polling with Event-Driven Refresh

**Problem**: `refresh_loop()` sleeps 0.5s and calls `_invalidate()` constantly. This wastes CPU and causes unnecessary renders.

**Changes**:
1. Remove the `refresh_loop()` thread entirely
2. Instead, call `self._invalidate()` directly in every state-changing method (already done — each `update_*` and `set_*` calls `_invalidate()`)
3. For agent running state, add a lightweight spinner refresh:
   ```python
   def _start_spinner_refresh(self):
       """Start a minimal refresh loop only when agent is actively working."""
       import threading
       def spinner_loop():
           while not self._should_exit:
               if self._cli._agent_running:
                   self._invalidate(min_interval=0.3)
               time.sleep(0.3)
       self._spinner_thread = threading.Thread(target=spinner_loop, daemon=True)
       self._spinner_thread.start()
   ```
4. Call `_start_spinner_refresh()` in `start()` before `app.run()`

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 7: Add Error Handling & Cleanup

**Problem**: `start()` has no error handling. No cleanup of resources on exit.

**Changes**:
1. Wrap `start()` body in try/except:
   ```python
   def start(self, on_submit=None, on_interrupt=None):
       self._on_submit = on_submit
       self._on_interrupt = on_interrupt
       self._should_exit = False

       try:
           layout, kb, input_area = self._build_layout()
           # ... rest of setup
           self._app = app
           self._start_spinner_refresh()
           app.run()
       except Exception as e:
           logger.error(f"Dashboard TUI failed: {e}", exc_info=True)
       finally:
           self._should_exit = True
           self._app = None
   ```
2. Add proper cleanup in `stop()`:
   ```python
   def stop(self):
       self._should_exit = True
       if self._app and self._app.is_running:
           try:
               self._app.exit()
           except Exception:
               pass
       self._app = None
   ```

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 8: Fix Unused Imports

**Problem**: Several imports are unused: `Buffer`, `Condition`, `ConditionalContainer`, `Float`, `FloatContainer`, `VSplit`, `WindowAlign`, `BufferControl`, `CompletionsMenu`, `ConditionalProcessor`, `PasswordProcessor`, `Processor`, `Transformation`, `SlashCommandAutoSuggest` (will be used after Task 3).

**Changes**:
1. Remove unused imports: `Buffer`, `ConditionalContainer`, `Float`, `FloatContainer`, `VSplit`, `WindowAlign`, `BufferControl`, `CompletionsMenu`, `ConditionalProcessor`, `PasswordProcessor`, `Processor`, `Transformation`
2. Keep: `Condition`, `FormattedText`, `KeyBindings`, `HSplit`, `Layout`, `Window`, `FormattedTextControl`, `Dimension`, `TextArea`, `Application`
3. Add: `FileHistory`, `AutoSuggestFromHistory` (for Task 3)

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 9: Add CompletionsMenu to Layout

**Problem**: No completions menu in the dashboard layout — tab completion won't show results visually.

**Changes**:
1. In `_build_layout()`, add `CompletionsMenu` to the layout:
   ```python
   from prompt_toolkit.layout.menus import CompletionsMenu
   completions_menu = CompletionsMenu(max_height=8, scroll_offset=1)
   ```
2. Add to `HSplit`:
   ```python
   layout = Layout(
       HSplit([
           main_window,
           focus_window,
           Window(char="─", height=1, style="class:dashboard-input-rule"),
           input_area,
           func_key_window,
           completions_menu,  # NEW
       ])
   )
   ```

**Files**: `aizen_cli/dashboard_tui.py`

---

## Task 10: Add Skin Engine Dynamic Color Refresh

**Problem**: Colors are loaded once in `__init__` and never refreshed. If user changes skin mid-session, dashboard won't update.

**Changes**:
1. Add method to refresh colors:
   ```python
   def _refresh_colors(self):
       """Reload colors from skin engine."""
       self._colors = _get_skin_colors()
       if self._app:
           self._app.style = PTStyle.from_dict(self._build_style())
   ```
2. Call `_refresh_colors()` in `invalidate()` if skin changed (or just call it periodically)
3. Add `@property` for colors that always fetch fresh:
   ```python
   @property
   def _colors(self):
       if not hasattr(self, "_cached_colors") or self._colors_stale:
           self._cached_colors = _get_skin_colors()
           self._colors_stale = False
       return self._cached_colors
   ```

**Files**: `aizen_cli/dashboard_tui.py`

---

## Final Verification Wave

After all tasks are complete:

1. **Syntax check**: `python -c "import ast; ast.parse(open('aizen_cli/dashboard_tui.py').read())"`
2. **Import check**: `python -c "from aizen_cli.dashboard_tui import DashboardTUI; print('OK')"`
3. **Run existing tests**: `python -m pytest tests/test_cli_background_tui_refresh.py -q`
4. **Run skin tests**: `python -m pytest tests/aizen_cli/test_skin_engine.py -q`
5. **Run banner tests**: `python -m pytest tests/aizen_cli/test_banner.py -q`
6. **Full test suite**: `python -m pytest tests/ -q --ignore=tests/gateway --ignore=tests/tools`
7. **Manual verification**: Start CLI with `display.tui_mode: dashboard` in config and verify:
   - Terminal resize works without breaking layout
   - Multiline input works (Alt+Enter inserts newline)
   - History navigation (Up/Down) works
   - Tab completion shows slash commands
   - Agent running state updates focus line
   - Conversation history appears in interaction area
   - No crashes on exit (Ctrl+D)

---

## Implementation Order

1. Task 8 (clean imports) → Task 1 (resize) → Task 2 (unicode) → Task 3 (input) → Task 4 (paste) → Task 5 (data wiring) → Task 6 (performance) → Task 7 (error handling) → Task 9 (completions menu) → Task 10 (skin refresh) → Verification

## Risk Assessment
- **Low risk**: Tasks 1-2, 6-8, 10 — pure refactoring, no behavioral change
- **Medium risk**: Tasks 3-4, 9 — input handling changes, need testing
- **Medium risk**: Task 5 — data wiring, depends on CLI state availability
- **Mitigation**: All changes are additive — classic TUI remains untouched
