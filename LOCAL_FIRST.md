# Hermes Agent — Local-First Guide

Hermes Agent is designed to work **without any API keys**. Every feature has a free, local alternative. API keys are purely optional — they unlock premium providers but are never required.

## Features That Work Without Any API Keys

| Feature | Local Provider | Description |
|---------|---------------|-------------|
| **Web Search** | DuckDuckGo (ddgs) | Free search via `pip install ddgs` — no key needed |
| **Text-to-Speech** | Edge-TTS | Free Microsoft Edge voices, no API key |
| **Text-to-Speech** | NeuTTS | On-device TTS via `neutts[all]`, runs on CPU/GPU |
| **Speech-to-Text** | faster-whisper | Local Whisper model, runs on CPU/GPU |
| **Vector Database** | ChromaDB | Persistent local vector store (`chromadb`) |
| **Vector Database** | FAISS | Facebook's high-performance similarity search (`faiss-cpu`/`faiss-gpu`) |
| **Browser** | Local Chromium | Headless local browser via `agent-browser` |
| **Browser** | Camofox | Local anti-detection browser (set `CAMOFOX_URL`) |
| **Session Storage** | SQLite + FTS5 | Full-text search across past conversations |
| **Memory** | Local memory_tool | SQLite-based persistent memory |
| **Terminal** | Local backend | Direct shell access, Docker, SSH |
| **File Operations** | Local filesystem | Read, write, search, patch files |
| **Code Execution** | Local sandbox | Python/Node.js execution |
| **Skills** | Local skills | All installed skills run locally |
| **Cron** | Local scheduler | Scheduled tasks via APScheduler |
| **Delegation** | Subagents | Run isolated child agents on same machine |

## Optional API Keys

All API keys in `~/.hermes/.env` are **optional**. Hermes works fully without them:

- **LLM Providers**: OpenRouter, Nous, Z.AI, Kimi, DeepSeek, DashScope, HuggingFace, etc. — you need at least one LLM provider, but free options exist (see below)
- **Web Search**: Exa, Parallel, Firecrawl, Tavily — DuckDuckGo is the free fallback
- **TTS**: ElevenLabs, OpenAI TTS — Edge-TTS and NeuTTS are free alternatives
- **STT**: Groq, OpenAI Whisper API — faster-whisper is the free local alternative
- **Browser**: Browserbase, Browser Use — local browser works without these
- **Image Generation**: FAL API — no free local alternative currently
- **Memory**: Honcho API — local memory_tool.py is the built-in alternative

## Free LLM Access

You can run Hermes with **zero cost** using free model providers:

- **OpenCode** — Free models via `opencode/` prefix (Qwen, MiniMax, Nemotron, etc.)
- **Nous Portal** — Free tier available
- **HuggingFace** — Free Inference Providers (20+ open models with `HF_TOKEN`)

## Local Alternatives Reference

### Vector Search
```bash
# ChromaDB — persistent local vector DB
pip install chromadb

# FAISS — Facebook's similarity search
pip install faiss-cpu   # CPU only
pip install faiss-gpu   # GPU accelerated
```

### Voice
```bash
# Edge-TTS — free Microsoft Edge voices (default provider)
pip install edge-tts

# NeuTTS — on-device neural TTS
pip install neutts[all]

# faster-whisper — local speech-to-text
pip install faster-whisper
```

### Web Search
```bash
# DuckDuckGo — free search, no API key
pip install ddgs
```

### Browser
```bash
# Local browser — included with Hermes
# No additional install needed — uses bundled agent-browser

# Camofox — anti-detection browsing
# Install separately, set CAMOFOX_URL env var
```

## Deprecated/Removed Features

The following API keys have been marked as deprecated because their associated skills were removed:

| Env Var | Status | Replacement |
|---------|--------|-------------|
| `HONCHO_API_KEY` | **Deprecated** | Use local `memory_tool.py` instead |
| `WANDB_API_KEY` | **Deprecated** | Moved to optional; no longer in core toolset |

See [DEAD_CODE_ANALYSIS.md](DEAD_CODE_ANALYSIS.md) for the full dead code analysis.

## Configuration

All local-first settings are in `~/.hermes/config.yaml`:

```yaml
# TTS — Edge-TTS is the default (free)
tts:
  provider: "edge"  # "edge" | "neutts" | "elevenlabs" | "openai"

# STT — faster-whisper is the default (free)
stt:
  provider: "local"  # "local" | "groq" | "openai"
  local:
    model: "base"  # tiny, base, small, medium, large-v3

# Web — DDGS is the free fallback
web:
  backend: "auto"  # auto-detects available backend
```

## Summary

**You can run Hermes Agent with zero API keys** if you:
1. Use a free LLM provider (OpenCode, Nous free tier, or HuggingFace)
2. Install `ddgs` for web search (`pip install ddgs`)
3. Use the default Edge-TTS for voice output
4. Use faster-whisper for voice input
5. Use local ChromaDB/FAISS for vector operations
6. Use the built-in local browser

Everything else — terminal, files, memory, cron, delegation — works locally out of the box.
