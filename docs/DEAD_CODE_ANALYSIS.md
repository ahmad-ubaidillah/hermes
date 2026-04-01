# Hermes Dead Code & Unusable Modules Analysis

**Generated:** 2025-04-01  
**Purpose:** Identify unused modules, dead code, and API-dependent modules with local alternatives

---

## Summary

This document maps dead code, unusable modules, and API-dependent features that have local alternatives in the Hermes codebase.

### Quick Stats
- **Dead Skills:** 13+ directories
- **Dead Tests:** 5+ test files
- **Dead Tool Imports:** 1 (honcho_tools.py - missing file)
- **API-Dependent Modules with Local Alternatives:** 8+ modules

---

## 1. DEAD SKILLS (API-Dependent, No Local Users)

These skills require external API keys and have been identified as unusable for local-first users. They should be removed or moved to `optional-skills/`.

### 1.1 Productivity Skills

| Skill | Path | API Required | Status |
|-------|------|--------------|--------|
| **google-workspace** | `skills/productivity/google-workspace/` | Google API OAuth | DEAD - Should remove |
| **linear** | `skills/productivity/linear/` | LINEAR_API_KEY | DEAD - Should remove |
| **notion** | `skills/productivity/notion/` | NOTION_API_KEY | DEAD - Should remove |

**Files to remove:**
```
skills/productivity/google-workspace/
├── SKILL.md
├── scripts/
│   ├── google_api.py
│   └── setup.py
└── references/

skills/productivity/linear/
└── SKILL.md

skills/productivity/notion/
└── SKILL.md
```

### 1.2 Social Media Skills

| Skill | Path | API Required | Status |
|-------|------|--------------|--------|
| **xitter** | `skills/social-media/xitter/` | Twitter/X API | DEAD - Should remove |

**Files to remove:**
```
skills/social-media/xitter/
└── SKILL.md
```

### 1.3 Smart Home Skills

| Skill | Path | API Required | Status |
|-------|------|--------------|--------|
| **openhue** | `skills/smart-home/openhue/` | Philips Hue API | DEAD - Should remove |

**Files to remove:**
```
skills/smart-home/openhue/
└── SKILL.md
```

### 1.4 Media Skills

| Skill | Path | API Required | Local Alternative | Status |
|-------|------|--------------|-------------------|--------|
| **gif-search** | `skills/media/gif-search/` | GIPHY/Tenor API | None needed | DEAD - Should remove |

**Files to remove:**
```
skills/media/gif-search/
└── SKILL.md
```

### 1.5 MLOps Skills (API-Dependent)

| Skill | Path | API Required | Local Alternative | Status |
|-------|------|--------------|-------------------|--------|
| **pinecone** | `optional-skills/mlops/pinecone/` | PINECONE_API_KEY | ChromaDB/FAISS | DEAD - Keep in optional |
| **lambda-labs** | `optional-skills/mlops/cloud/lambda-labs/` | LAMBDA_API_KEY | Local GPU | DEAD - Keep in optional |
| **modal** | `skills/mlops/cloud/modal/` | MODAL_TOKEN | Local execution | DEAD - Should move to optional |
| **weights-and-biases** | `skills/mlops/evaluation/weights-and-biases/` | WANDB_API_KEY | SQLite/JSON logging | DEAD - Should move to optional |
| **inference-sh** | `skills/inference-sh/` | INFERENCE_SH_API | Local models | DEAD - Only has DESCRIPTION.md |

---

## 2. DEAD TOOL IMPORTS

### 2.1 Missing Tool File

| Module | Import Path | Issue |
|--------|-------------|-------|
| **honcho_tools** | `tools.honcho_tools` | File does not exist but imported in `tools/model_tools.py` |

**Location in code:**
```python
# tools/model_tools.py line ~150
_modules = [
    ...
    "tools.honcho_tools",  # <-- FILE DOES NOT EXIST
    ...
]
```

**Impact:** This causes a warning at startup but doesn't break functionality since honcho code is embedded in `run_agent.py`.

---

## 3. DEAD TESTS

Tests for removed/unusable features should be cleaned up:

| Test File | Purpose | Status |
|-----------|---------|--------|
| `tests/gateway/test_honcho_lifecycle.py` | Honcho integration | DEAD - Remove |
| `tests/test_honcho_client_config.py` | Honcho config | DEAD - Remove |
| `tests/tools/test_honcho_tools.py` | Honcho tools | DEAD - Remove |
| `tests/integration/test_modal_terminal.py` | Modal cloud terminal | DEAD - Remove |
| `tests/tools/test_modal_sandbox_fixes.py` | Modal sandbox | DEAD - Remove |
| `tests/skills/test_google_oauth_setup.py` | Google Workspace OAuth | DEAD - Remove |

---

## 4. HONCHO INTEGRATION (Special Case)

Honcho is a cloud-based memory service from NousResearch. It has extensive code but users prefer the local alternative.

### Honcho Code Locations

| File | Lines | Description |
|------|-------|-------------|
| `run_agent.py` | ~300+ | Honcho integration code |
| `agent/display.py` | ~10 | Honcho session URL helpers |
| `hermes_cli/config.py` | ~20 | HONCHO_API_KEY config |
| `docs/honcho-integration-spec.md` | ~400 | Integration spec |
| `docs/honcho-integration-spec.html` | ~700 | HTML version |

### Local Alternative: memory_tool.py

**File:** `tools/memory_tool.py`

**Features:**
- File-backed persistent memory (MEMORY.md, USER.md)
- No API required
- Character-based limits (not tokens)
- Frozen snapshot pattern for cache stability
- Threat pattern scanning for security

**Recommendation:** 
- Keep honcho as OPTIONAL feature (requires HONCHO_API_KEY)
- Default to local memory_tool.py for all users
- Move honcho code to separate module if possible

---

## 5. API-DEPENDENT MODULES WITH LOCAL ALTERNATIVES

### 5.1 Web Tools (web_tools.py)

| Feature | API Required | Local Alternative |
|---------|--------------|-------------------|
| web_search | EXA_API_KEY / PARALLEL_API_KEY / TAVILY_API_KEY | DuckDuckGo (free) |
| web_extract | FIRECRAWL_API_KEY / PARALLEL_API_KEY | Lightpanda (local) |
| web_crawl | FIRECRAWL_API_KEY | Lightpanda (local) |

**Recommendation:** Add DuckDuckGo as default free search provider

### 5.2 Browser Tools (browser_tool.py)

| Feature | API Required | Local Alternative |
|---------|--------------|-------------------|
| Browserbase cloud | BROWSERBASE_API_KEY | Local Chromium via agent-browser |
| Browser Use cloud | BROWSER_USE_API_KEY | Local Chromium via agent-browser |
| Camofox anti-detect | CAMOFOX_URL | Local Chromium (no anti-detect) |

**Status:** Already has local alternative! Cloud is optional.

### 5.3 TTS Tools (tts_tool.py)

| Provider | API Required | Local Alternative |
|----------|--------------|-------------------|
| ElevenLabs | ELEVENLABS_API_KEY | Edge-TTS (free) / NeuTTS (local) |
| OpenAI TTS | VOICE_TOOLS_OPENAI_KEY | Edge-TTS (free) |
| NeuTTS | Local | Already local! |

**Status:** Already has local alternatives! Default is Edge-TTS (free).

### 5.4 Image Generation (image_generation_tool.py)

| Provider | API Required | Local Alternative |
|----------|--------------|-------------------|
| FAL | FAL_KEY | Stable Diffusion (local) |
| | | ComfyUI (local) |

**Recommendation:** Add local Stable Diffusion support

### 5.5 RL Training (rl_training_tool.py)

| Feature | API Required | Local Alternative |
|---------|--------------|-------------------|
| Tinker API | TINKER_API_KEY | Local Atropos environments |
| WandB logging | WANDB_API_KEY | Local SQLite/JSON |

**Status:** Has local Atropos environments but requires Tinker for cloud training

### 5.6 Vector Databases

| Provider | API Required | Local Alternative |
|----------|--------------|-------------------|
| Pinecone | PINECONE_API_KEY | ChromaDB (local) / FAISS (local) |
| Qdrant | Self-hosted option | Already can be local |

**Status:** ChromaDB and FAISS are already available as local alternatives

---

## 6. UNUSED/LEGACY TOOLS

These tools exist in `tools/` but are not in the `_discover_tools()` import list:

| Tool | Status | Notes |
|------|--------|-------|
| `ansi_strip.py` | USED | Helper for display |
| `approval.py` | USED | Command approval system |
| `browser_camofox.py` | USED | Camofox browser backend |
| `checkpoint_manager.py` | USED | RL training checkpoints |
| `credential_files.py` | USED | Credential management |
| `debug_helpers.py` | USED | Debug utilities |
| `env_passthrough.py` | USED | Environment handling |
| `file_operations.py` | USED | File operations |
| `fuzzy_match.py` | USED | Fuzzy matching |
| `hash_edit.py` | USED | Hash-based editing |
| `interrupt.py` | USED | Interrupt handling |
| `lsp_client.py` | USED | LSP integration |
| `mcp_oauth.py` | USED | MCP OAuth |
| `mcp_serve.py` | USED | MCP server |
| `mcp_tool.py` | USED | MCP client |
| `neutts_synth.py` | USED | NeuTTS synthesis |
| `openrouter_client.py` | USED | OpenRouter client |
| `patch_parser.py` | USED | Patch parsing |
| `registry.py` | USED | Tool registry |
| `rewind_store.py` | USED | Rewind store |
| `skills_guard.py` | USED | Skill security scanner |
| `skills_hub.py` | USED | Skills Hub |
| `skills_sync.py` | USED | Skill syncing |
| `tirith_security.py` | USED | Command security |
| `transcription_tools.py` | USED | Voice transcription |
| `url_safety.py` | USED | URL safety checks |
| `voice_mode.py` | USED | Voice mode for gateway |
| `website_policy.py` | USED | Website access policy |

**Note:** These are NOT dead code - they are imported/used by other modules but not directly in `_discover_tools()` because they're helper modules, not standalone tools.

---

## 7. FILES TO DELETE

### Skills to Remove (from `skills/` directory)
```
skills/productivity/google-workspace/
skills/productivity/linear/
skills/productivity/notion/
skills/social-media/xitter/
skills/smart-home/openhue/
skills/media/gif-search/
skills/mlops/cloud/modal/          # Move to optional-skills
skills/mlops/evaluation/weights-and-biases/  # Move to optional-skills
skills/inference-sh/               # Only has DESCRIPTION.md
```

### Tests to Remove
```
tests/gateway/test_honcho_lifecycle.py
tests/test_honcho_client_config.py
tests/tools/test_honcho_tools.py
tests/integration/test_modal_terminal.py
tests/tools/test_modal_sandbox_fixes.py
tests/skills/test_google_oauth_setup.py
```

### Code to Fix
```python
# tools/model_tools.py - Remove or comment out:
# "tools.honcho_tools",  # File does not exist
```

---

## 8. RECOMMENDATIONS

### Priority 1: Remove Dead Skills
1. Delete skills that require external APIs with no local users
2. Move useful but API-dependent skills to `optional-skills/`

### Priority 2: Fix Missing Imports
1. Remove `tools.honcho_tools` from `_discover_tools()` or create the file

### Priority 3: Clean Up Tests
1. Remove tests for deleted skills
2. Remove tests for API-dependent features (modal, honcho)

### Priority 4: Document Local Alternatives
1. Update documentation to highlight local-first approach
2. Add migration guides for users moving from cloud to local

---

## 9. LOCAL-FIRST STACK (What to Keep)

| Category | Tool | Type |
|----------|------|------|
| Memory | memory_tool.py | File-based (MEMORY.md/USER.md) |
| Vector DB | ChromaDB / FAISS | Local |
| Browser | Local Chromium via agent-browser | Local |
| TTS | Edge-TTS / NeuTTS | Free/Local |
| Search | DuckDuckGo | Free |
| Notes | Obsidian | Local |
| Email | Himalaya | CLI |
| Crawler | Lightpanda | Local |
| Knowledge | SQLite/JSONL | Local |

---

## 10. ACTION ITEMS

- [x] Delete dead skill directories (DONE 2025-04-01)
- [x] Remove dead test files (DONE 2025-04-01)
- [x] Fix `tools.honcho_tools` import error (DONE 2025-04-01 - commented out)
- [x] Move modal and weights-and-biases to `optional-skills/` (DONE 2025-04-01)
- [x] Update OPTIONAL_ENV_VARS in config.py to mark dead APIs (DONE 2025-04-01)
- [x] Add DuckDuckGo as default search provider (DONE 2025-04-01)
- [x] Document local-first approach in README (DONE 2025-04-01 - created LOCAL_FIRST.md)

---

## 11. COMPLETED CLEANUP LOG

**Date:** 2025-04-01

### Deleted Skills (7 directories)
- `skills/productivity/google-workspace/` - DELETED
- `skills/productivity/linear/` - DELETED
- `skills/productivity/notion/` - DELETED
- `skills/social-media/xitter/` - DELETED
- `skills/smart-home/openhue/` - DELETED
- `skills/media/gif-search/` - DELETED
- `skills/inference-sh/` - DELETED

### Deleted Tests (6 files)
- `tests/gateway/test_honcho_lifecycle.py` - DELETED
- `tests/test_honcho_client_config.py` - DELETED
- `tests/tools/test_honcho_tools.py` - DELETED
- `tests/integration/test_modal_terminal.py` - DELETED
- `tests/tools/test_modal_sandbox_fixes.py` - DELETED
- `tests/skills/test_google_oauth_setup.py` - DELETED

### Fixed Import
- `tools/model_tools.py` - Commented out `"tools.honcho_tools"` import (line 161)

### Moved to optional-skills (2 directories)
- `skills/mlops/cloud/modal/` → `optional-skills/mlops/cloud/modal/`
- `skills/mlops/evaluation/weights-and-biases/` → `optional-skills/mlops/evaluation/weights-and-biases/`
