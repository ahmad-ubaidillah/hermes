# Aizen Agent Roadmap

**Autonomous AI Team Platform - Build software with minimal human intervention**

---

## Vision

Aizen is an autonomous AI agent platform that can execute complex software development tasks with minimal human supervision. The platform leverages AI tools, skills, and multi-agent collaboration to handle end-to-end development workflows.

---

## Current Status (2026)

### ✅ Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| Core Agent | ✅ | AIAgent class with tool calling |
| CLI Interface | ✅ | Interactive chat + commands |
| Gateway | ✅ | Telegram, Discord, Slack, WhatsApp |
| Tools (35+) | ✅ | File, terminal, web, browser, code exec |
| Skills (100+) | ✅ | Software development, research, etc |
| Profiles | ✅ | Multi-instance isolation |
| Cron Jobs | ✅ | Background automation |
| MCP Server | ✅ | ACP protocol support |

### 🆕 Recently Added

| Feature | Status |
|---------|--------|
| Doom Loop Detection | ✅ |
| L0/L1/L2 Context Engine | ✅ |
| Vector DB (ChromaDB) | ✅ |
| Permission System | ✅ |
| Auto Pip-Install | ✅ |
| Self-Healing Execution | ✅ |
| Task Extraction Agent | ✅ |
| Skill Memory Layer | ✅ |
| Wisdom Accumulation | ✅ |
| Planning Agents (Prometheus/Metis/Momus) | ✅ |
| Hash-Anchored Edits | ✅ |
| Kanban System | ✅ |
| Bughunter | ✅ |

---

## Future Roadmap

### Phase 1: Core Improvements (Q2 2026)

- [ ] **Enhanced Context Compression** - Better token optimization
- [ ] **Improved Tool Calling** - Higher success rate for edits
- [ ] **Multi-Modal Support** - Image/video understanding
- [ ] **Better Error Recovery** - Auto-retry with smarter strategies

### Phase 2: Collaboration (Q3 2026)

- [ ] **Multi-Agent Teams** - Multiple Aizen agents working together
- [ ] **Agent-to-Agent Communication** - Inter-agent messaging
- [ ] **Distributed Execution** - Run agents on remote machines
- [ ] **Shared Context** - Team memory across sessions

### Phase 3: Autonomy (Q4 2026)

- [ ] **Self-Improving Agents** - Learn from past tasks
- [ ] **Automated Testing** - Self-generate and run tests
- [ ] **Code Review Automation** - Auto-review PRs
- [ ] **Deployment Pipeline** - End-to-end CI/CD

### Phase 4: Intelligence (2027)

- [ ] **Reasoning Models** - Integrate advanced reasoning
- [ ] **Knowledge Graph** - Semantic understanding
- [ ] **Long-Term Memory** - Persistent learning
- [ ] **Agent Marketplace** - Share and discover skills

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Aizen Platform                    │
├─────────────────────────────────────────────────────┤
│  CLI  │  Gateway  │  MCP Server  │  ACP Adapter     │
├─────────────────────────────────────────────────────┤
│              Core Agent (AIAgent)                    │
│  ├─ Context Engine (L0/L1/L2)                        │
│  ├─ Tool Orchestrator                               │
│  ├─ Self-Healing                                    │
│  └─ Doom Loop Detection                            │
├─────────────────────────────────────────────────────┤
│  Tools (35+)                                        │
│  ├─ File Operations                                 │
│  ├─ Terminal                                        │
│  ├─ Web Search                                      │
│  ├─ Browser Automation                              │
│  └─ Code Execution                                  │
├─────────────────────────────────────────────────────┤
│  Skills (100+)                                      │
│  ├─ Software Development                            │
│  ├─ Research                                        │
│  ├─ DevOps                                          │
│  └─ Creative                                        │
└─────────────────────────────────────────────────────┘
```

---

## Comparison with Aigo

| Feature | Aigo | Aizen |
|---------|------|-------|
| Tools | 12 | 35+ |
| Skills | ❌ | 100+ |
| Distillation Pipeline | ❌ | ✅ |
| Gateway Platforms | 4 | 6 |
| Doom Loop Detection | ❌ | ✅ |
| Context Engine | ❌ | ✅ |
| Vector DB | ❌ | ✅ |
| Permission System | ❌ | ✅ |
| Self-Healing | ❌ | ✅ |
| Planning Agents | ❌ | ✅ |

---

## Contributing

See CONTRIBUTING.md for guidelines.

---

## License

MIT License - See LICENSE file
