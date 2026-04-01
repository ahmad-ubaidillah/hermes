# Aizen vs Claw Code (Claude Code) Comparison

## Overview

**Claw Code** is a Python porting workspace for the original Claude Code TypeScript implementation. It tracks **207 commands**, **hundreds of tools**, and **29 subsystems** from the original Claude Code.

**Aizen** is a mature, production-ready AI agent framework with **31658 Python files**, extensive tool ecosystem, and multi-platform gateway support.

---

## Feature Comparison Matrix

### Core Agent Features

| Feature | Claude Code (Claw) | Aizen | Status |
|---------|-------------------|--------|--------|
| **Agent Loop** | ✅ TypeScript | ✅ Python | ✅ Aizen has |
| **Tool Orchestration** | ✅ 100+ tools | ✅ 50+ tools | ✅ Aizen has |
| **Session Management** | ✅ | ✅ SessionDB | ✅ Aizen has |
| **Context Compression** | ✅ | ✅ trajectory_compressor | ✅ Aizen has |
| **Multi-model Support** | ✅ Anthropic only | ✅ Multi-provider | ⭐ Aizen BETTER |

### CLI Features

| Feature | Claude Code (Claw) | Aizen | Status |
|---------|-------------------|--------|--------|
| **Interactive CLI** | ✅ Ink (React-like) | ✅ Rich + prompt_toolkit | ✅ Aizen has |
| **Slash Commands** | ✅ 207 commands | ✅ ~30 commands | ⚠️ Aizen less |
| **Auto-complete** | ✅ | ✅ | ✅ Aizen has |
| **Skins/Themes** | ❓ | ✅ 4 skins | ⭐ Aizen BETTER |
| **REPL Mode** | ✅ | ❌ | ⚠️ Aizen MISSING |

### Gateway/Messaging

| Feature | Claude Code (Claw) | Aizen | Status |
|---------|-------------------|--------|--------|
| **Telegram** | ❓ | ✅ | ⭐ Aizen has |
| **Discord** | ❓ | ✅ | ⭐ Aizen has |
| **Slack** | ❓ | ✅ | ⭐ Aizen has |
| **WhatsApp** | ❓ | ✅ | ⭐ Aizen has |
| **Signal** | ❓ | ✅ | ⭐ Aizen has |
| **Home Assistant** | ❓ | ✅ | ⭐ Aizen has |

### Integration Features

| Feature | Claude Code (Claw) | Aizen | Status |
|---------|-------------------|--------|--------|
| **MCP Support** | ✅ Native | ✅ Native MCP client | ✅ Both have |
| **VS Code Integration** | ✅ | ✅ ACP adapter | ✅ Aizen has |
| **Git Integration** | ✅ | ✅ 7 git skills | ✅ Aizen has |
| **Browser Automation** | ✅ | ✅ Browserbase | ✅ Aizen has |

### Development Features

| Feature | Claude Code (Claw) | Aizen | Status |
|---------|-------------------|--------|--------|
| **Skills System** | ✅ plugins | ✅ 100+ skills | ⭐ Aizen BETTER |
| **Memory System** | ❓ | ✅ Chroma + FAISS | ⭐ Aizen BETTER |
| **Cron/Scheduling** | ❓ | ✅ Built-in | ⭐ Aizen BETTER |
| **Multi-Agent** | ❓ | ✅ 18 agents | ⭐ Aizen BETTER |

---

## Claude Code Unique Features (Aizen Missing)

### 1. **Bridge System** (31 modules)
Claude Code has a sophisticated bridge system for remote sessions:
- `bridge/bridgeApi.ts` - Remote API
- `bridge/bridgeMessaging.ts` - Cross-process messaging
- `bridge/jwtUtils.ts` - JWT authentication
- `bridge/remoteBridgeCore.ts` - Remote bridge core
- `bridge/codeSessionApi.ts` - Code session management

**Aizen Gap**: No built-in remote session bridge. Would need to add.

### 2. **Voice System**
Claude Code has voice integration subsystem:
- Voice input/output
- Speech recognition integration

**Aizen Gap**: No voice support. Could integrate with whisper/elevenlabs.

### 3. **Vim Integration**
Claude Code has vim-specific features:
- Vim keybindings
- Vim mode integration

**Aizen Gap**: No vim-specific features.

### 4. **Keybindings System**
Claude Code has configurable keybindings:
- Custom keybinding profiles
- Keyboard shortcuts management

**Aizen Gap**: Limited keybinding support (only CLI basic).

### 5. **Buddy/Companion System**
Claude Code has an animated companion:
- `CompanionSprite.tsx` - Animated sprite
- `useBuddyNotification.tsx` - Companion notifications

**Aizen Gap**: No animated companion feature.

### 6. **Screens System**
Claude Code has screen management:
- Multiple screen layouts
- Screen transitions

**Aizen Gap**: No screen management system.

### 7. **Services Layer**
Claude Code has a services abstraction:
- Service registry
- Service lifecycle

**Aizen Gap**: No formal service layer.

### 8. **Bootstrap System**
Claude Code has bootstrap state management:
- `bootstrap/state.ts` - Bootstrap state machine
- Initialization orchestration

**Aizen Gap**: No formal bootstrap system.

### 9. **Native TypeScript Bridge**
Claude Code has native TS integration:
- `native_ts/` - Native TypeScript execution

**Aizen Gap**: No native TypeScript execution.

### 10. **Output Styles**
Claude Code has configurable output styles:
- `outputStyles/` - Different output formatting

**Aizen Gap**: Limited output style options.

---

## Claude Code Commands Analysis (207 total)

### Command Categories Aizen Should Consider:

#### Navigation Commands (Missing in Aizen):
- `/add-dir` - Add directory to context
- `/remove-dir` - Remove directory from context

#### Session Commands (Aizen has some):
- `/compact` - Compact context (Aizen has)
- `/clear` - Clear conversation (Aizen has)
- `/resume` - Resume session (Aizen has)

#### Agent Commands (Aizen has):
- `/agents` - List agents (Aizen has multi-agent)
- `/fork` - Fork subagent (Aizen has delegate_task)

#### Development Commands (Missing in Aizen):
- `/bughunter` - Bug hunting mode
- `/autofix-pr` - Auto-fix PR
- `/chrome` - Chrome integration
- `/statusline` - Status line integration

#### Bridge Commands (Missing in Aizen):
- `/bridge` - Bridge mode
- `/bridge-kick` - Kick bridge connection

#### Utility Commands (Missing in Aizen):
- `/brief` - Brief output mode
- `/btw` - Side notes
- `/advisor` - Advisor mode
- `/ant-trace` - Ant trace visualization

---

## Aizen Unique Features (Claude Code Missing)

### 1. **Multi-Platform Gateway**
- Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant
- Claude Code is CLI-only

### 2. **Multi-Agent Team System**
- 18 specialized agents (CEO, DEV, QA, ARCH, etc.)
- Sprint workflow, standups, retrospectives

### 3. **Comprehensive Skills System**
- 100+ skills in 15+ categories
- Local-first approach

### 4. **Vector Database Integration**
- ChromaDB + FAISS for semantic search
- Knowledge store

### 5. **Cron/Scheduling**
- Built-in job scheduler
- Automated standups and reports

### 6. **Production Readiness**
- Graceful shutdown
- Process supervision
- Health checks
- Resilience patterns

### 7. **Multi-Provider Support**
- Anthropic, OpenAI, OpenRouter, OpenCode (free models)
- Claude Code is Anthropic-only

### 8. **RL Training Environments**
- Atropos integration
- Agent training frameworks

---

## Priority Recommendations for Aizen

### High Priority (Should Add):

1. **REPL Mode** - Interactive Python REPL for debugging
2. **Voice Integration** - Speech input/output via whisper/tts
3. **Remote Bridge** - WebSocket-based remote session support
4. **Better Keybindings** - Configurable keyboard shortcuts

### Medium Priority (Nice to Have):

5. **Buddy/Companion** - Optional animated assistant
6. **Output Styles** - More formatting options
7. **Services Layer** - Formal service abstraction
8. **Bootstrap System** - Startup state machine

### Low Priority (Can Skip):

9. **Vim Integration** - Niche feature
10. **Native TS Bridge** - Python-first approach is fine
11. **Screen Management** - CLI is sufficient

---

## File Count Comparison

| Project | Python Files | TypeScript Files | Total Lines |
|---------|-------------|------------------|-------------|
| Aizen | 31658 | 0 | ~500K+ |
| Claw Code | 67 | 0 (archived) | ~10K |

**Note**: Aizen is significantly more mature and feature-complete than Claw Code. Claw Code is primarily a tracking/manifest system for the original TypeScript codebase.

---

## Conclusion

**Aizen is MORE feature-complete** than Claw Code in most areas:

✅ **Aizen Advantages**:
- Multi-platform gateway
- Multi-agent orchestration
- Comprehensive skills system
- Production-ready infrastructure
- Multi-provider support

⚠️ **Aizen Gaps**:
- Voice integration
- Remote bridge system
- REPL debugging mode
- Vim/keybinding support
- Companion/buddy feature

**Recommendation**: Focus on adding REPL mode and voice integration as the highest-value missing features.
