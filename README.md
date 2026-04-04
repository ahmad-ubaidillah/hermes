<p align="center">
  <img src="assets/jellyfish.svg" alt="Aizen Agent Jellyfish" width="200">
</p>

<p align="center">
  <pre>
    ___    _________   _______   __   ___   _____________   ________
   /   |  /  _/__  /  / ____/ | / /  /   | / ____/ ____/ | / /_  __/
  / /| |  / /   / /  / __/ /  |/ /  / /| |/ / __/ __/ /  |/ / / /   
 / ___ |_/ /   / /__/ /___/ /|  /  / ___ / /_/ / /___/ /|  / / /    
/_/  |_/___/  /____/_____/_/ |_/  /_/  |_\____/_____/_/ |_/ /_/     
  </pre>
</p>

<p align="center">
  <b>Execute with Zen</b>
</p>

<p align="center">
  <i>Assign. Review. Repeat.</i>
</p>

<p align="center">
  <a href="https://github.com/ahmad-ubaidillah/hermes"><img src="https://img.shields.io/badge/GitHub-ahmad--ubaidillah/hermes-181717?style=for-the-badge&logo=github" alt="GitHub"></a>
  <a href="https://github.com/ahmad-ubaidillah/aizen/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Version-3.1.0-blue?style=for-the-badge" alt="Version">
</p>

---

**Autonomous AI Team Platform — Build software with minimal human intervention**

---

## What is Aizen Agent?

Aizen Agent is an autonomous AI team platform that helps you build software with minimal human intervention. 

| Feature | Description |
|---------|-------------|
| **<z> Agent** | Chat with Aizen - your AI coding companion |
| **Distillation Pipeline** | 70-90% token reduction via context compression |
| **Doom Loop Detection** | Auto-detect and escape infinite retry loops |
| **L0/L1/L2 Context Engine** | Three-tier context with automatic compaction |
| **Self-Healing Execution** | Auto-retry failed operations with smart strategies |
| **Permission System** | allow/deny/ask modes for tool access control |
| **Auto Pip-Install** | Automatic package installation for missing imports |
| **Hash-Anchored Edits** | Zero stale-line file editing (68.3% success rate) |
| **Planning Agents** | Prometheus (planner), Metis (gap analyzer), Momus (reviewer) |
| **Skill Memory Layer** | Learn from successful task patterns |
| **Wisdom Accumulation** | Extract and reuse lessons from past tasks |
| **100+ Skills** | Modular skills for different workflows |
| **6 Gateway Platforms** | Telegram, Discord, Slack, WhatsApp, etc. |

---

## Quick Start

```bash
# Install (one line!)
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash

# Chat with Aizen
aizen

# Use free models via OpenCode
aizen --model opencode/qwen3.6-plus-free
```

---

## Installation

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash
```

This will:
- Install uv (fast Python package manager)
- Clone Aizen to `~/.aizen/aizen-agent`
- Create Python 3.11 virtual environment
- Install all dependencies
- Check for OpenCode (install if missing)
- Create `aizen` command
- Run setup wizard (optional)
- Auto-configure PAGER=cat for better CLI experience

### Manual Install

```bash
git clone https://github.com/ahmad-ubaidillah/hermes.git ~/.aizen/aizen-agent
cd ~/.aizen/aizen-agent
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv venv --python 3.11
source venv/bin/activate
uv pip install -e ".[all]"
aizen setup
```

---

## Configuration

Run `aizen setup` to configure interactively, or create `~/.aizen/config.yaml`:

```yaml
# Model configuration (choose one)
model: opencode/qwen3.6-plus-free  # Free via OpenCode
# model: openai/gpt-4             # Via OpenAI
# model: anthropic/claude-opus-4  # Via OpenRouter

# Display settings
display:
  tool_progress: true
  skin: default

# Agent settings
max_iterations: 90
```

---

## Usage Examples

```bash
# Basic chat
aizen

# With specific model
aizen --model opencode/mimo-v2-omni-free

# Quick query
aizen -q "what files are in this directory?"

# Debug mode
aizen --debug

# Run skill
aizen /skill codebase-inspection
```

---

## Advanced Features

### Doom Loop Detection
Automatically detects when the agent is stuck in a failure loop and triggers recovery strategies.

### Context Engine (L0/L1/L2)
Three-tier context management:
- **L0 (Hot)**: Current conversation context
- **L1 (Warm)**: Recent session history  
- **L2 (Cold)**: Long-term memory via vector DB

### Self-Healing Execution
Automatically retries failed operations with exponential backoff:
- Syntax errors → fix and retry
- Import errors → auto-install missing packages
- Permission errors → request approval
- Rate limits → wait and retry
- Network errors → retry with backoff

### Planning Agents
- **Prometheus**: Breaks down complex tasks into actionable steps
- **Metis**: Identifies gaps and ambiguities in task descriptions
- **Momus**: Reviews execution plans for quality and completeness

---

## Free Models (via OpenCode)

Aizen auto-detects OpenCode credentials for seamless free model access:

| Model | Description |
|-------|-------------|
| `opencode/qwen3.6-plus-free` | Fast, capable coding |
| `opencode/mimo-v2-omni-free` | Multimodal |
| `opencode/minimax-m2.5-free` | Long context |
| `opencode/nemotron-3-super-free` | NVIDIA |

---

## Skills

Aizen comes with 100+ built-in skills:

| Category | Skills |
|----------|--------|
| **Software Dev** | code-review, test-driven-development, systematic-debugging |
| **DevOps** | `arch-dev-setup`, `pre-commit-checks`, `hermes-autostart` |
| **GitHub** | `github-pr-workflow`, `github-issues`, `code-review` |
| **Creative** | `ascii-art`, `excalidraw`, `songwriting` |
| **MLOps** | `unsloth`, `axolotl`, `lm-evaluation-harness` |
| **Research** | `ml-paper-writing`, `polymarket` |
| **System** | `chroma-vector-db`, `local-task-board`, `linux-scripts` |

Browse all skills: `aizen /skills`

---

## Gateway Platforms

Connect Aizen to your favorite messaging platforms:

| Platform | Status |
|----------|--------|
| Telegram | ✅ |
| Discord | ✅ |
| Slack | ✅ |
| WhatsApp | ✅ |
| Home Assistant | ✅ |
| Signal | ✅ |

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Credits

Fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com)

---

<p align="center">
  <b>Execute with Zen ⚕ Assign. Review. Repeat.</b>
</p>
