# Rebranding Plan: Hermes → Aizen

## Brand Identity

### Logo
```
<z>
```
- `<>` = Code brackets (developer/programmer identity)
- `z` = Zen (simplicity, clarity, enlightenment)
- Minimalist, clean, memorable

### Name
- **Aizen** - from Japanese "ai" (合) + "zen" (禅) = harmony + zen
- Alternative: Aizen from Bleach (calm, powerful, strategic)

### Color Scheme
| Element | Hex | Usage |
|---------|-----|-------|
| Primary | `#7C3AED` | Purple/Violet - main brand |
| Secondary | `#A78BFA` | Light purple - accents |
| Accent | `#10B981` | Emerald - success/active |
| Dark | `#1E1B4B` | Deep purple - backgrounds |
| Light | `#F5F3FF` | Soft purple - text backgrounds |

### ASCII Art Logo
```
[bold #7C3AED]    ___    [/]
[bold #7C3AED]   <   >   [/]
[#A78BFA]    < z >    [/]
[bold #7C3AED]   <   >   [/]
[bold #7C3AED]    ‾‾‾    [/]
[#10B981]  AIZEN  [/]
[dim]  Code • Zen • Clarity[/]
```

Alternative compact:
```
[#7C3AED]<z>[/][dim] Aizen - AI Agent Framework[/]
```

---

## Rebranding Tasks

### Phase 1: Core Renaming (Automated)

#### 1.1 Package & Entry Points
- [ ] `pyproject.toml`: `hermes-agent` → `aizen-agent`
- [ ] CLI command: `hermes` → `aizen`
- [ ] Folder: `hermes_cli/` → `aizen_cli/`
- [ ] Folder: `hermes_state.py` → `aizen_state.py`
- [ ] Module: `core.hermes_constants` → `core.aizen_constants`

#### 1.2 Environment Variables
- [ ] All `HERMES_*` → `AIZEN_*` (~50 variables)
- [ ] Config directory: `~/.hermes/` → `~/.aizen/`
- [ ] Migration script for existing users

#### 1.3 Code References
- [ ] All `"hermes"` string references → `"aizen"`
- [ ] Class names with Hermes prefix → Aizen prefix
- [ ] Function names with hermes_ → aizen_
- [ ] Comments and docstrings

### Phase 2: Visual Rebranding

#### 2.1 CLI Banner
- [ ] New ASCII art logo `<z>`
- [ ] New color scheme (purple/violet)
- [ ] New tagline: "Code • Zen • Clarity"
- [ ] Update `hermes_cli/banner.py`

#### 2.2 Skin Engine
- [ ] New default skin with purple theme
- [ ] Update `hermes_cli/skin_engine.py`
- [ ] Update spinner colors and faces
- [ ] Update agent name branding

#### 2.3 Display Module
- [ ] Update spinner defaults
- [ ] Update color constants
- [ ] Update `agent/display.py`

### Phase 3: Web Dashboard

#### 3.1 Frontend Branding
- [ ] Update `web/frontend/src/App.tsx`
- [ ] Change title to "Aizen Dashboard"
- [ ] Update colors to purple theme
- [ ] Update logo/favicon

#### 3.2 API & Backend
- [ ] Update API routes if needed
- [ ] Update CORS origins
- [ ] Update error messages

### Phase 4: Setup Wizard

#### 4.1 Wizard UI
- [ ] Update `hermes_cli/setup_wizard.py`
- [ ] New welcome message
- [ ] New branding text
- [ ] Update prompts

#### 4.2 Setup Scripts
- [ ] `setup-hermes.sh` → `setup-aizen.sh`
- [ ] Update installation instructions

### Phase 5: Documentation

#### 5.1 Core Docs
- [ ] README.md - full rewrite
- [ ] AGENTS.md - update references
- [ ] docs/*.md - update all

#### 5.2 Code Comments
- [ ] All "Hermes" in comments → "Aizen"
- [ ] Update author references

### Phase 6: Migration & Compatibility

#### 6.1 Migration Script
- [ ] Create `scripts/migrate_hermes_to_aizen.py`
- [ ] Move `~/.hermes/` → `~/.aizen/`
- [ ] Update config.yaml references
- [ ] Migrate session databases
- [ ] Update environment variables in `.env`

#### 6.2 Backward Compatibility (Optional)
- [ ] Support both HERMES_* and AIZEN_* env vars
- [ ] Deprecation warnings for old names
- [ ] Symlink ~/.hermes → ~/.aizen

### Phase 7: Testing & Cleanup

#### 7.1 Test Updates
- [ ] Update all test files
- [ ] Fix test fixtures
- [ ] Update mock paths

#### 7.2 CI/CD
- [ ] Update GitHub Actions workflows
- [ ] Update Docker image names
- [ ] Update PyPI package (if publishing)

---

## File Changes Summary

### Directories to Rename
```
hermes_cli/          → aizen_cli/
hermes_state.py      → aizen_state.py
core/hermes_constants.py → core/aizen_constants.py
tests/hermes_cli/    → tests/aizen_cli/
setup-hermes.sh      → setup-aizen.sh
```

### Files to Update (Major)
```
pyproject.toml               # Package name, CLI entry point
cli.py                       # CLI class name, branding
run_agent.py                 # Agent class, imports
model_tools.py               # Tool references
gateway/run.py               # Gateway branding
hermes_cli/banner.py         # ASCII art, colors
hermes_cli/skin_engine.py    # Default skin
hermes_cli/setup_wizard.py   # Wizard branding
agent/display.py             # Display constants
web/frontend/src/App.tsx     # Web UI branding
```

### Environment Variables (~50 total)
```bash
# Core
HERMES_HOME          → AIZEN_HOME
HERMES_MODEL         → AIZEN_MODEL
HERMES_API_KEY       → AIZEN_API_KEY
HERMES_PROVIDER      → AIZEN_PROVIDER
HERMES_CONFIG        → AIZEN_CONFIG

# Logging
HERMES_LOG_LEVEL     → AIZEN_LOG_LEVEL
HERMES_LOG_FILE      → AIZEN_LOG_FILE

# Tools
HERMES_TOOL_PROGRESS → AIZEN_TOOL_PROGRESS
HERMES_CORE_TOOLS    → AIZEN_CORE_TOOLS

# Features
HERMES_CRON_*        → AIZEN_CRON_*
HERMES_BRIDGE_*      → AIZEN_BRIDGE_*
HERMES_CODEX_*       → AIZEN_CODEX_*
# ... etc
```

---

## Execution Plan

### Step 1: Automated Find-Replace
```bash
# String replacements
find . -type f -name "*.py" -exec sed -i 's/hermes/aizen/g' {} +
find . -type f -name "*.py" -exec sed -i 's/Hermes/Aizen/g' {} +
find . -type f -name "*.py" -exec sed -i 's/HERMES_/AIZEN_/g' {} +

# Config paths
find . -type f -name "*.py" -exec sed -i 's/\.hermes/.aizen/g' {} +
```

### Step 2: Directory Renaming
```bash
mv hermes_cli aizen_cli
mv core/hermes_constants.py core/aizen_constants.py
mv tests/hermes_cli tests/aizen_cli
```

### Step 3: Manual Updates
- Banner ASCII art (new `<z>` logo)
- Color scheme in skin_engine
- Web UI components

### Step 4: Migration Script
```python
# scripts/migrate_hermes_to_aizen.py
import shutil
from pathlib import Path

old_home = Path.home() / ".hermes"
new_home = Path.home() / ".aizen"

if old_home.exists() and not new_home.exists():
    shutil.move(str(old_home), str(new_home))
    # Update config.yaml, .env, etc.
```

---

## Risk Mitigation

1. **Backup First**
   - Git commit before starting
   - Tag current version as `v3.x-hermes-final`

2. **Gradual Rollout**
   - Test thoroughly before pushing
   - Keep migration script tested

3. **User Communication**
   - Update README with migration guide
   - Version bump to 4.0.0 (major version = breaking change)

---

## Success Criteria

- [ ] All `hermes` references replaced with `aizen`
- [ ] All `HERMES_*` env vars work as `AIZEN_*`
- [ ] CLI launches as `aizen` command
- [ ] Config directory is `~/.aizen/`
- [ ] New banner shows `<z>` logo with purple theme
- [ ] Web dashboard shows Aizen branding
- [ ] Setup wizard shows Aizen branding
- [ ] All tests pass
- [ ] CI/CD green
- [ ] Migration script works for existing users
