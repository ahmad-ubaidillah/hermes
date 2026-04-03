# Aizen Agent - Comprehensive Documentation

## Table of Contents
1. [What is Aizen?](#what-is-aizen)
2. [Why Does Aizen Exist?](#why-does-aizen-exist)
3. [Methodology](#methodology)
4. [Key Features](#key-features)
5. [Advantages](#advantages)
6. [Agents](#agents)
7. [Skills](#skills)
8. [Modules](#modules)
9. [Tools](#tools)

---

## What is Aizen?

Aizen Agent is an autonomous AI team platform designed to help developers build software with minimal human intervention. It is an AI coding assistant that combines multiple specialized agents, a flexible skill system, and extensive tool integrations to create a powerful development workflow.

The name "Aizen" comes from the Japanese word "愛染" meaning "true love" or "affection," symbolizing the bond between developer and AI assistant. The platform follows the mantra **"Execute with Zen ⚕ Assign. Review. Repeat."**

Aizen is a fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research, extended with additional features for modern software development.

---

## Why Does Aizen Exist?

Aizen was created to address several challenges in AI-assisted software development:

### 1. Fragmented Workflow
Traditional AI coding assistants work in isolation. Aizen provides a unified platform where multiple specialized agents can collaborate on complex tasks.

### 2. Limited Context Window
Aizen implements intelligent context compression and prompt caching to maximize the effective context window of LLMs, allowing for longer conversations and larger codebases.

### 3. Platform Lock-in
Aizen supports multiple messaging platforms (Telegram, Discord, Slack, WhatsApp) and can run locally with llama.cpp, giving users flexibility in how they interact with the AI.

### 4. Skill Reusability
The skill system allows developers to create reusable workflows that can be shared and invoked across different projects and teams.

### 5. Autonomous Operation
Aizen is designed to operate with minimal human intervention, handling complex multi-step tasks while keeping the human in the loop for critical decisions.

---

## Methodology

Aizen employs several methodologies to deliver its functionality:

### 1. Multi-Agent Orchestration
Aizen uses a hierarchical agent system where different agents specialize in specific tasks. The main agent (Aizen) acts as a coordinator, delegating tasks to specialized sub-agents.

### 2. Tool Calling
Aizen implements a robust tool calling system based on the OpenAI function calling API. Models can call tools to perform actions like reading files, running terminal commands, or searching the web.

### 3. Context Compression
When conversations exceed the model's context window, Aizen automatically compresses the context while preserving important information.

### 4. Prompt Caching
Aizen caches system prompts to reduce token usage and improve response times, particularly important for Anthropic and OpenAI models.

### 5. Provider-Aware Routing
Aizen intelligently routes requests to different LLM providers based on model requirements, context length, and cost considerations.

### 6. Skill Injection
Skills are injected as user messages (not system prompts) to maintain prompt caching efficiency while providing domain-specific knowledge.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **<z> Agent** | Chat with Aizen - your AI coding companion |
| **IntentGate** | Smart intent classification - routes tasks to appropriate agents |
| **Parallel Agents** | Run 5+ agents concurrently with priority queues |
| **48 Lifecycle Hooks** | Fine-grained control over agent lifecycle |
| **Hash-Anchored Edit** | Zero stale-line file editing - precise code modifications |
| **Web Dashboard** | FastAPI + React dashboard for monitoring agent activity |
| **Skill System** | Modular skills for different workflows |
| **Multi-Platform** | Telegram, Discord, Slack, WhatsApp integration |
| **Local Models** | Support for llama.cpp, Ollama, LM Studio |
| **MCP Support** | Model Context Protocol client for external tools |

---

## Advantages

### 1. Open Source & Self-Hosted
Aizen can be run entirely locally, giving users full control over their data and the AI models they use.

### 2. Free Models via OpenCode
Access to free models through OpenCode integration without API costs.

### 3. Extensive Tool Integration
Native support for file operations, terminal commands, web browsing, browser automation, and code execution.

### 4. Flexible Configuration
Highly configurable through YAML files and environment variables, with support for multiple profiles.

### 5. Developer Experience
Rich CLI with autocomplete, multiple skins/themes, and interactive setup wizards.

### 6. Enterprise-Ready
Session persistence, FTS5 search, and cron job scheduling for automated workflows.

---

## Agents

Aizen consists of specialized AI agents, each with a specific role:

| Agent | Role | Focus |
|-------|------|-------|
| **Aizen** | CEO | Decision making, coordination, task assignment |
| **Atlas** | Master Orchestrator | Task delegation, verification, quality control |
| **Cody** | Developer | Implementation, coding, bug fixes |
| **Nova** | PM | Requirements analysis, backlog management |
| **Testa** | QA | Testing, bug reports, quality assurance |

### Agent Hierarchy

```
Aizen (Main Agent)
├── Atlas (Orchestrator)
│   ├── Sisyphus-Junior (Task Executor)
│   │   ├── Explore (Code Search)
│   │   ├── Librarian (Codebase Understanding)
│   │   ├── Oracle (Debugging)
│   │   ├── Metis (Planning)
│   │   └── Momus (Review)
│   └── Subagents (User-Delegated)
└── Specialized Tools (Terminal, File, Web, Browser)
```

---

## Skills

Aizen includes 100+ built-in skills organized by category:

### DevOps Skills
- `arch-dev-setup` - Development environment setup
- `pre-commit-checks` - Pre-commit hook management
- `hermes-autostart` - Service auto-start configuration

### GitHub Skills
- `github-pr-workflow` - Pull request automation
- `github-issues` - Issue management
- `code-review` - Automated code review

### Creative Skills
- `ascii-art` - ASCII art generation
- `excalidraw` - Diagram creation
- `songwriting` - Lyrics generation

### MLOps Skills
- `unsloth` - LLM fine-tuning with Unsloth
- `axolotl` - Axolotl training framework
- `lm-evaluation-harness` - Model evaluation

### System Skills
- `chroma-vector-db` - ChromaDB integration
- `local-task-board` - Kanban-style task management
- `linux-scripts` - Linux automation scripts

### Available Skills

```
Browse skills: aizen /skills
Use skill:    aizen /skill <skill-name>
```

---

## Modules

Aizen is organized into several core modules:

### Core Modules

| Module | Description |
|--------|-------------|
| `run_agent.py` | AIAgent class - core conversation loop |
| `model_tools.py` | Tool orchestration and discovery |
| `toolsets.py` | Toolset definitions |
| `cli.py` | AizenCLI class - interactive CLI |
| `aizen_state.py` | SessionDB - SQLite session storage |

### Agent Internals (`agent/`)

| Module | Description |
|--------|-------------|
| `prompt_builder.py` | System prompt assembly |
| `context_compressor.py` | Auto context compression |
| `prompt_caching.py` | Anthropic prompt caching |
| `auxiliary_client.py` | Auxiliary LLM client |
| `model_metadata.py` | Model context lengths |
| `models_dev.py` | models.dev registry |
| `display.py` | UI display utilities |
| `skill_commands.py` | Skill slash commands |
| `trajectory.py` | Trajectory saving |

### CLI Modules (`aizen_cli/`)

| Module | Description |
|--------|-------------|
| `main.py` | Entry point |
| `config.py` | Configuration management |
| `commands.py` | Slash command registry |
| `callbacks.py` | Terminal callbacks |
| `setup.py` | Setup wizard |
| `skin_engine.py` | Theme/skin engine |
| `skills_config.py` | Skill configuration |
| `tools_config.py` | Tool configuration |
| `skills_hub.py` | Skill hub browser |
| `models.py` | Model catalog |
| `model_switch.py` | Model switching |
| `auth.py` | Provider credentials |

### Gateway Modules (`gateway/`)

| Module | Description |
|--------|-------------|
| `run.py` | Main gateway loop |
| `session.py` | Session persistence |
| `platforms/` | Telegram, Discord, Slack, WhatsApp adapters |

---

## Tools

Aizen provides extensive tools organized into toolsets. The core tools (`_AIZEN_CORE_TOOLS`) are available across all platforms.

### File Tools
- `read_file` - Read file contents
- `write_file` - Write/create files
- `patch` - Hash-anchored file editing
- `search_files` - Grep-style file search

### Terminal Tools
- `terminal` - Execute shell commands
- `process` - Manage background processes
- `execute_code` - Run code in sandbox

### Web Tools
- `web_search` - Web search
- `web_extract` - Web content extraction

### Browser Automation
- `browser_navigate` - Navigate URLs
- `browser_snapshot` - Take screenshots
- `browser_click` - Click elements
- `browser_type` - Type input
- `browser_scroll` - Scroll pages
- `browser_console` - Browser console access

### Planning & Memory
- `todo` - Task management
- `memory` - Persistent memory
- `session_search` - Search conversation history

### Collaboration
- `delegate_task` - Delegate to subagents
- `clarify` - Ask clarifying questions

### Special Tools
- `skills_list` - List available skills
- `skill_view` - View skill details
- `skill_manage` - Manage skills
- `vision_analyze` - Image analysis
- `image_generate` - Image generation
- `text_to_speech` - TTS output
- `send_message` - Cross-platform messaging
- `cronjob` - Job scheduling

### Home Assistant
- `ha_list_entities` - List HA entities
- `ha_get_state` - Get entity state
- `ha_list_services` - List HA services
- `ha_call_service` - Call HA service

### OpenCode Integration
- `opencode_coding_task` - Create coding task
- `opencode_edit_file` - Request file edit
- `opencode_review_code` - Request code review
- `opencode_explain_code` - Request explanation
- `opencode_generate_code` - Request code generation
- `opencode_status` - Check task status

---

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash

# Chat with Aizen
aizen

# Use free models
aizen --model opencode/qwen3.6-plus-free

# Run a skill
aizen /skill codebase-inspection
```

---

## Configuration

Aizen configuration is stored in `~/.aizen/config.yaml`:

```yaml
model: opencode/qwen3.6-plus-free
max_iterations: 90

display:
  tool_progress: true
  skin: default

agent:
  enabled_toolsets:
    - research
    - coding
```

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Credits

Aizen is a fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com).
