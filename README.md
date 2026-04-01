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
  <a href="https://github.com/ahmad-ubaidillah/aizen"><img src="https://img.shields.io/badge/GitHub-ahmad--ubaidillah/aizen-181717?style=for-the-badge&logo=github" alt="GitHub"></a>
  <a href="https://github.com/ahmad-ubaidillah/aizen/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Version-3.0.0-blue?style=for-the-badge" alt="Version">
</p>

---

**Autonomous AI Team Platform — Build software with minimal human intervention**

---

## What is Aizen Agent?

Aizen Agent is an autonomous AI team platform that helps you build software with minimal human intervention. 

| Feature | Description |
|---------|-------------|
| **<z> Agent** | Chat with Aizen - your AI coding companion |
| **IntentGate** | Smart intent classification - routes tasks to appropriate agents |
| **Parallel Agents** | Run 5+ agents concurrently with priority queues |
| **48 Lifecycle Hooks** | Fine-grained control over agent lifecycle |
| **Hash-Anchored Edit** | Zero stale-line file editing |
| **Web Dashboard** | FastAPI + React dashboard for monitoring |
| **Skill System** | Modular skills for different workflows |

---

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/aizen/main/scripts/install.sh | bash

# Chat with Aizen
aizen

# Use free models
aizen --model opencode/qwen3.6-plus-free
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AIZEN AGENT v3.0                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│     ┌─────────┐     ┌──────────┐     ┌──────────┐         │
│     │  User   │────▶│  <z>     │────▶│  Agents  │         │
│     │ Input   │     │  Aizen   │     │  (5+)    │         │
│     └─────────┘     └──────────┘     └──────────┘         │
│                           │                                 │
│                           ▼                                 │
│     ┌─────────┐     ┌──────────┐     ┌──────────┐         │
│     │  Hooks  │◀───▶│  Skills  │◀───▶│  Tools   │         │
│     │  (48)   │     │ (100+)   │     │  (20+)   │         │
│     └─────────┘     └──────────┘     └──────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/aizen/main/scripts/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/ahmad-ubaidillah/aizen.git ~/.aizen/aizen-agent
cd ~/.aizen/aizen-agent
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv venv --python 3.11
source venv/bin/activate
uv pip install -e ".[all]"
aizen setup
```

---

## Configuration

Create `~/.aizen/config.yaml`:

```yaml
# Model configuration
model: opencode/qwen3.6-plus-free
provider: opencode

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
aizen --model openai/gpt-4

# Debug mode
aizen --debug

# Run skill
aizen /skill codebase-inspection
```

---

## Skills

Aizen comes with 100+ built-in skills:

| Category | Skills |
|----------|--------|
| **DevOps** | `arch-dev-setup`, `pre-commit-checks`, `hermes-autostart` |
| **GitHub** | `github-pr-workflow`, `github-issues`, `code-review` |
| **Creative** | `ascii-art`, `excalidraw`, `songwriting` |
| **MLOps** | `unsloth`, `axolotl`, `lm-evaluation-harness` |
| **System** | `chroma-vector-db`, `local-task-board`, `linux-scripts` |

Browse all skills: `aizen /skills`

---

## Team Agents

Aizen Agent includes specialized AI agents:

| Agent | Role | Focus |
|-------|------|-------|
| **Aizen** | CEO | Decision making, coordination |
| **Atlas** | Architect | System design, tech decisions |
| **Cody** | Developer | Implementation, coding |
| **Nova** | PM | Requirements, backlog |
| **Testa** | QA | Testing, bug reports |

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Credits

Fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com)

---

<p align="center">
  <b>Execute with Zen • Assign. Review. Repeat.</b>
</p>
