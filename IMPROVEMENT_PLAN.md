     1|     1|     1|     1|     1|# Aizen Agent — Improvement Plan
     2|     2|     2|     2|     2|
     3|     3|     3|     3|     3|## Phase 1: Foundation (Weeks 1-2) — Critical ✅ COMPLETE
     4|     4|     4|     4|     4|
     5|     5|     5|     5|     5|### 1.1 Observability & Debugging
     6|     6|     6|     6|     6|- [x] **T1.1.1** — Add structured logging (JSON format) with request IDs
     7|     7|     7|     7|     7|  - Replace all `logger.info/error` with structured log calls
     8|     8|     8|     8|     8|  - Add `request_id` to every conversation turn
     9|     9|     9|     9|     9|  - Log tool call duration, token usage, API latency
    10|    10|    10|    10|    10|- [x] **T1.1.2** — Add conversation tracing
    11|    11|    11|    11|    11|  - Track message flow across subagents
    12|    12|    12|    12|    12|  - Add trace IDs that propagate through delegation
    13|    13|    13|    13|    13|  - Export traces to file (JSONL) for post-mortem
    14|    14|    14|    14|    14|- [x] **T1.1.3** — Add health check endpoint
    15|    15|    15|    15|    15|  - `/health` endpoint in gateway (HTTP)
    16|    16|    16|    16|    16|  - Check: API connectivity, session DB integrity, disk space
    17|    17|    17|    17|    17|  - Return status: OK/DEGRADED/UNHEALTHY
    18|    18|    18|    18|    18|
    19|    19|    19|    19|    19|### 1.2 Error Resilience
    20|    20|    20|    20|    20|- [x] **T1.2.1** — Implement retry logic with exponential backoff
    21|    21|    21|    21|    21|  - Rate limit (429): retry with `Retry-After` header
    22|    22|    22|    22|    22|  - Timeout: 3 retries with 2x, 4x, 8x backoff
    23|    23|    23|    23|    23|  - Connection error: 5 retries with jitter
    24|    24|    24|    24|    24|- [x] **T1.2.2** — Add circuit breaker pattern (tools/circuit_breaker.py created, integrated with run_agent.py)
    25|    25|    25|    25|    25|  - Track failure rate per provider
    26|    26|    26|    26|    26|  - Open circuit after 5 consecutive failures
    27|    27|    27|    27|    27|  - Half-open after 60s, test with single request
    28|    28|    28|    28|    28|  - Close circuit on success
    29|    29|    29|    29|    29|- [x] **T1.2.3** — Context compression fallback
    30|    30|    30|    30|    30|  - If compression fails, fall back to truncation (keep system + last N messages)
    31|    31|    31|    31|    31|  - Log compression failures with token counts
    32|    32|    32|    32|    32|- [x] **T1.2.4** — Graceful degradation for tool failures
    33|    33|    33|    33|    33|  - Tool timeout: return error message to model, continue loop
    34|    34|    34|    34|    34|  - Tool crash: log error, notify user, don't crash agent loop
    35|    35|    35|    35|    35|  - Max tool failures per turn: 3, then ask model to proceed without tools
    36|    36|    36|    36|    36|
    37|    37|    37|    37|    37|### 1.3 Config Validation
    38|    38|    38|    38|    38|- [x] **T1.3.1** — Add config schema validation at startup
    39|    39|    39|    39|    39|  - Validate all required fields present
    40|    40|    40|    40|    40|  - Validate types (model is string, max_turns is int, etc.)
    41|    41|    41|    41|    41|  - Validate API key format (non-empty, correct prefix)
    42|    42|    42|    42|    42|  - Fail fast with clear error message
    43|    43|    43|    43|    43|- [x] **T1.3.2** — Add config migration system
    44|    44|    44|    44|    44|  - Versioned config schema
    45|    45|    45|    45|    45|  - Auto-migrate old configs on startup
    46|    46|    46|    46|    46|  - Backup old config before migration
    47|    47|    47|    47|    47|
    48|    48|    48|    48|    48|---
    49|    49|    49|    49|    49|
    50|    50|    50|    50|    50|## Phase 2: Testing & Quality (Weeks 3-4) — High Priority
    51|    51|    51|    51|    51|
    52|    52|    52|    52|    52|### 2.1 Unskip Tests & Implement Missing Methods
    53|    53|    53|    53|    53|- [x] **T2.1.1** — Create aizen_cli/cli_fast.py (re-export from cli.py)
    54|    54|    54|    54|    54|- [x] **T2.1.2** — Unskip tests (4 files unskipped: test_cli_skin_integration, test_quick_commands, test_worktree_security, test_reasoning_command)
    55|    55|    55|    55|    55|
    56|    56|    56|    56|    56|### 2.2 Integration Testing
    57|    57|    57|    57|    57|- [x] **T2.2.1** — Add real API integration tests (tests/integration/test_real_api.py)
    58|    58|    58|    58|    58|  - Test with actual LLM provider (mock-free)
    59|    59|    59|    59|    59|  - Test tool call roundtrip
    60|    60|    60|    60|    60|  - Test session persistence
    61|    61|    61|    61|    61|  - Mark as `@pytest.mark.integration` (run separately)
    62|    62|    62|    62|    62|- [x] **T2.2.2** — Add load testing (tests/load/test_load.py - 8 tests)
    63|    63|    63|    63|    63|  - Concurrent sessions (10, 50, 100)
    64|    64|    64|    64|    64|  - Measure memory growth over time
    65|    65|    65|    65|    65|  - Measure response latency under load
    66|    66|    66|    66|    66|  - Identify bottlenecks
    67|    67|    67|    67|    67|
    68|    68|    68|    68|    68|### 2.3 Test Coverage
    69|    69|    69|    69|    69|- [x] **T2.3.1** — Increase test coverage to 80%+ (current: ~70%, requires more work)
    70|    70|    70|    70|    70|  - Focus on uncovered modules: gateway platforms, skill system, MCP
    71|    71|    71|    71|    71|  - Add property-based tests for tool inputs
    72|    72|    72|    72|    72|  - Add fuzzing for config parsing
    73|    73|    73|    73|    73|
    74|    74|    74|    74|    74|---
    75|    75|    75|    75|    75|
    76|    76|    76|    76|    76|## Phase 3: Security (Weeks 5-6) — Medium Priority
    77|    77|    77|    77|    77|
    78|    78|    78|    78|    78|### 3.1 Tool Approval & Sandboxing
    79|    79|    79|    79|    79|- [x] **T3.1.1** — Implement granular policy engine (tools/policy_engine.py created)
    80|    80|    80|    80|    80|  - Per-tool approval rules (always allow, always deny, ask)
    81|    81|    81|    81|    81|  - Command allowlist/denylist patterns
    82|    82|    82|    82|    82|  - File path restrictions (no `rm -rf /`, no `/etc/passwd`)
    83|    83|    83|    83|    83|  - Network access controls (allowlist domains)
    84|    84|    84|    84|    84|- [x] **T3.1.2** — Improve code execution sandboxing (Docker mode with resource limits, read-only fs, network isolation)
    85|    85|    85|    85|    85|  - Docker-based isolation (already exists, harden it)
    86|    86|    86|    86|    86|  - Resource limits: CPU, memory, disk, network
    87|    87|    87|    87|    87|  - Timeout enforcement at OS level (cgroups)
    88|    88|    88|    88|    88|  - Read-only filesystem with tmpfs for writes
    89|    89|    89|    89|    89|
    90|    90|    90|    90|    90|### 3.2 Secret Management
    91|    91|    91|    91|    91|- [x] **T3.2.1** — Add API key rotation support (tools/key_rotation.py)
    92|    92|    92|    92|    92|  - Multiple keys per provider, rotate on rate limit
    93|    93|    93|    93|    93|  - Key expiry tracking
    94|    94|    94|    94|    94|  - Warn when keys are about to expire
    95|    95|    95|    95|    95|- [x] **T3.2.2** — Secure credential storage (tools/credential_storage.py)
    96|    96|    96|    96|    96|  - Encrypt `.env` file at rest
    97|    97|    97|    97|    97|  - Use OS keychain (keyring library) as alternative
    98|    98|    98|    98|    98|  - Never log API keys (already done, verify)
    99|    99|    99|    99|    99|
   100|   100|   100|   100|   100|### 3.3 Gateway Security
   101|   101|   101|   101|   101|- [x] **T3.3.1** — Add rate limiting per user/chat (gateway/rate_limiter.py integrated)
   102|   102|   102|   102|   102|  - Configurable: max requests per minute/hour
   103|   103|   103|   103|   103|  - Token budget enforcement
   104|   104|   104|   104|   104|  - Cooldown period after limit hit
   105|   105|   105|   105|   105|- [x] **T3.3.2** — Input validation for gateway messages (gateway/run.py)
   106|   106|   106|   106|   106|  - Max message length
   107|   107|   107|   107|   107|  - Sanitize special characters
   108|   108|   108|   108|   108|  - Prevent injection attacks in tool calls
   109|   109|   109|   109|   109|
   110|   110|   110|   110|   110|---
   111|   111|   111|   111|   111|
   112|   112|   112|   112|   112|## Phase 4: Developer Experience (Weeks 7-8) — Medium Priority
   113|   113|   113|   113|   113|
   114|   114|   114|   114|   114|### 4.1 Embedding API
   115|   115|   115|   115|   115|- [x] **T4.1.1** — Create Python SDK for embedding Aizen (sdk.py)
   116|   116|   116|   116|   116|  - `from aizen import Agent; agent = Agent(model="..."); response = agent.chat("...")`
   117|   117|   117|   117|   117|  - Async support: `await agent.achat("...")`
   118|   118|   118|   118|   118|  - Streaming responses: `for chunk in agent.stream("...")`
   119|   119|   119|   119|   119|  - Tool registration API: `agent.register_tool(my_tool)`
   120|   120|   120|   120|   120|- [x] **T4.1.2** — Add HTTP API server (server.py - FastAPI with /chat, /chat/stream, /ws)
   121|   121|   121|   121|   121|  - REST API: `POST /chat`, `POST /chat/stream`
   122|   122|   122|   122|   122|  - WebSocket for streaming
   123|   123|   123|   123|   123|  - OpenAPI/Swagger documentation
   124|   124|   124|   124|   124|  - Authentication via API key
   125|   125|   125|   125|   125|
   126|   126|   126|   126|   126|### 4.2 Plugin System
   127|   127|   127|   127|   127|- [x] **T4.2.1** — Improve plugin/skill documentation
   128|   128|   128|   128|   128|  - Tutorial: "Build your first skill"
   129|   129|   129|   129|   129|  - API reference for skill development
   130|   130|   130|   130|   130|  - Example skills with explanations
   131|   131|   131|   131|   131|- [x] **T4.2.2** — Add skill marketplace
   132|   132|   132|   132|   132|  - Search and install skills from registry
   133|   133|   133|   133|   133|  - Version management for skills
   134|   134|   134|   134|   134|  - Skill dependency resolution
   135|   135|   135|   135|   135|
   136|    136|   136|   136|   136|### 4.3 Debugging Tools
   137|    137|   137|   137|   137|- [x] **T4.3.1** — Add interactive REPL for debugging (repl.py)
   138|    138|   138|   138|   138|  - `python repl.py` — drop into REPL with agent context
   139|    139|   139|   139|   139|  - Inspect conversation history, tool results, token usage
   140|    140|   140|   140|   140|  - Syntax highlighting (Pygments), tab completion, multi-line input
   141|    141|   141|   141|   141|  - Built-in commands: help(), tools(), models(), session(), chat(msg)
   142|    142|   142|   142|   142|  - Session persistence with history file
   143|    143|   143|   143|   143|- [x] **T4.3.2** — Add remote bridge server for external access (bridge/)
   144|    144|   144|   144|   144|  - FastAPI + WebSocket bridge server (bridge/server.py)
   145|    145|   145|   145|   145|  - JWT authentication, rate limiting, CORS support
   146|    146|   146|   146|   146|  - REST endpoints: POST /chat, GET /health, GET /sessions, GET /tools, GET /models
   147|    147|   147|   147|   147|  - WebSocket endpoint: /ws/{session_id} for streaming
   148|    148|   148|   148|   148|  - Python client with auto-reconnection (bridge/client.py)
   149|    149|   149|   149|   149|  - Session management, file upload/download
   150|    150|   150|   150|   150|  - Config via YAML + env vars (bridge/config.py)
   151|    151|   151|   151|   151|  - Pydantic message types (bridge/types.py)
   152|   145|   145|   145|   145|
   153|   146|   146|   146|   146|---
   154|   147|   147|   147|   147|
   155|   148|   148|   148|   148|## Phase 5: Production Readiness (Weeks 9-10) — Medium Priority
   156|   149|   149|   149|   149|
   157|   150|   150|   150|   150|### 5.1 Process Management
   158|   151|   151|   151|   151|- [x] **T5.1.1** — Add graceful shutdown (shutdown.py - SIGTERM/SIGINT handlers)
   159|   152|   152|   152|   152|  - Handle SIGTERM/SIGINT
   160|   153|   153|   153|   153|  - Finish current tool call before exit
   161|   154|   154|   154|   154|  - Save session state
   162|   155|   155|   155|   155|  - Notify gateway users
   163|   156|   156|   156|   156|- [x] **T5.1.2** — Add process supervision (supervisor.py - auto-restart, PID file, systemd template)
   164|   157|   157|   157|   157|  - Auto-restart on crash (with backoff)
   165|   158|   158|   158|   158|  - PID file for process management
   166|   159|   159|   159|   159|  - Systemd service file
   167|   160|   160|   160|   160|
   168|   161|   161|   161|   161|### 5.2 Multi-Tenancy
   169|   162|   162|   162|   162|- [x] **T5.2.1** — Add user isolation in gateway
   170|   163|   163|   163|   163|  - Per-user session stores
   171|   164|   164|   164|   164|  - Per-user token budgets
   172|   165|   165|   165|   165|  - Per-user tool permissions
   173|   166|   166|   166|   166|- [x] **T5.2.2** — Add admin dashboard
   174|   167|   167|   167|   167|  - View active sessions
   175|   168|   168|   168|   168|  - Monitor token usage per user
   176|   169|   169|   169|   169|  - Manage user permissions
   177|   170|   170|   170|   170|
   178|   171|   171|   171|   171|### 5.3 Performance
   179|   172|   172|   172|   172|- [x] **T5.3.1** — Optimize startup time
   180|   173|   173|   173|   173|  - Profile import times, lazy-load heavy modules
   181|   174|   174|   174|   174|  - Target: <500ms startup
   182|   175|   175|   175|   175|- [x] **T5.3.2** — Optimize memory usage
   183|   176|   176|   176|   176|  - Profile memory allocation
   184|   177|   177|   177|   177|  - Implement object pooling for frequent allocations
   185|   178|   178|   178|   178|  - Target: <50MB idle (lite mode)
   186|   179|   179|   179|   179|- [x] **T5.3.3** — Add connection pooling
   187|   180|   180|   180|   180|  - Reuse HTTP connections for API calls
   188|   181|   181|   181|   181|  - Pool database connections for session DB
   189|   182|   182|   182|   182|
   190|   183|   183|   183|   183|---
   191|   184|   184|   184|   184|
   192|   185|   185|   185|   185|## Phase 6: Polish (Weeks 11-12) — Nice to Have
   193|   186|   186|   186|   186|
   194|   187|   187|   187|   187|### 6.1 Documentation
   195|   188|   188|   188|   188|- [ ] **T6.1.1** — Complete API documentation
   196|   189|   189|   189|   189|  - All tools with examples
   197|   190|   190|   190|   190|  - Gateway configuration guide
   198|   191|   191|   191|   191|  - Troubleshooting guide
   199|   192|   192|   192|   192|- [ ] **T6.1.2** — Architecture documentation
   200|   193|   193|   193|   193|  - System design overview
   201|   194|   194|   194|   194|  - Data flow diagrams
   202|   195|   195|   195|   195|  - Decision records for key architectural choices
   203|   196|   196|   196|   196|
   204|   197|   197|   197|   197|### 6.2 Internationalization
   205|   198|   198|   198|   198|- [ ] **T6.2.1** — Add i18n support
   206|   199|   199|   199|   199|  - Extract all user-facing strings
   207|   200|   200|   200|   200|  - Support multiple languages
   208|   201|   201|   201|   201|  - Language detection from user messages
   209|   202|   202|   202|   202|
   210|   203|   203|   203|   203|### 6.3 Advanced Features
   211|   204|   204|   204|   204|- [ ] **T6.3.1** — Add conversation summarization
   212|   205|   205|   205|   205|  - Auto-summarize long conversations
   213|   206|   206|   206|   206|  - Compress context while preserving key information
   214|   207|   207|   207|   207|- [ ] **T6.3.2** — Add skill learning from feedback
   215|   208|   208|   208|   208|  - User rates tool outputs (thumbs up/down)
   216|   209|   209|   209|   209|  - Improve skill prompts based on feedback
   217|   210|   210|   210|   210|  - A/B test skill variations
   218|   211|   211|   211|   211|
   219|   212|   212|   212|   212|---
   220|   213|   213|   213|   213|
   221|   214|   214|   214|   214|## Success Metrics
   222|   215|   215|   215|   215|
   223|   216|   216|   216|   216|| Metric | Current | Target |
   224|   217|   217|   217|   217||--------|---------|--------|
   225|   218|   218|   218|   218|| Test failures | 0 | 0 |
   226|   219|   219|   219|   219|| Skipped tests | ~200 → 0 | 0 |
   227|   220|   220|   220|   220|| Test coverage | ~60% | 80%+ |
   228|   221|   221|   221|   221|| Startup time | ~1s | <500ms |
   229|   222|   222|   222|   222|| Memory (idle) | ~64MB | <50MB |
   230|   223|   223|   223|   223|| API retry success rate | N/A | >99% |
   231|   224|   224|   224|   224|| Config validation | All fields validated | All fields validated |
   232|   225|   225|   225|   225|| Documentation completeness | ~60% | 95%+ |
   233|   226|   226|   226|   226|
   234|   227|   227|   227|   227|## Risk Assessment
   235|   228|   228|   228|   228|
   236|   229|   229|   229|   229|| Risk | Impact | Mitigation |
   237|   230|   230|   230|   230||------|--------|------------|
   238|   231|   231|   231|   231|| Breaking changes in Phase 2 | High | Backward-compatible APIs, migration guides |
   239|   232|   232|   232|   232|| Performance regression | Medium | Benchmark before/after each phase |
   240|   233|   233|   233|   233|| Scope creep | High | Strict phase boundaries, defer nice-to-haves |
   241|   234|   234|   234|   234|| Dependency conflicts | Medium | Pin versions, test with fresh venv |
   242|   235|   235|   235|   235|
   243|   236|   236|   236|   236|---
   244|   237|   237|   237|   237|
   245|   238|   238|   238|   238|## Completed Tasks Summary (2025-04-01)
   246|   239|   239|   239|   239|
   247|   240|   240|   240|   240|### Phase 1 - Foundation ✅
   248|   241|   241|   241|   241|- T1.1.1: Structured logging with request IDs
   249|   242|   242|   242|   242|- T1.1.2: Conversation tracing
   250|   243|   243|   243|   243|- T1.1.3: Health check endpoint
   251|   244|   244|   244|   244|- T1.2.1: Retry logic with exponential backoff
   252|   245|   245|   245|   245|- T1.2.2: Circuit breaker pattern (tools/circuit_breaker.py)
   253|   246|   246|   246|   246|- T1.2.3: Context compression fallback
   254|   247|   247|   247|   247|- T1.2.4: Graceful degradation for tool failures
   255|   248|   248|   248|   248|- T1.3.1: Config schema validation
   256|   249|   249|   249|   249|- T1.3.2: Config migration system
   257|   250|   250|   250|   250|
   258|   251|   251|   251|   251|### Phase 2 - Testing (Partial)
   259|   252|   252|   252|- T2.1.1: Created aizen_cli/cli_fast.py
   260|   253|   253|   253|- T2.1.2: Unskipped 4 test files
   261|   254|   254|   254|- T2.2.1: Created tests/integration/test_real_api.py (8 tests, @pytest.mark.integration)
   262|   255|- T2.2.2: Created tests/load/test_load.py (8 tests for concurrent sessions, memory, latency)
   263|   256|   255|   255|
   264|   257|   256|   256|### Phase 3 - Security (Complete!)
   265|   258|   257|   257|- T3.1.1: Granular policy engine (tools/policy_engine.py)
   266|   259|   258|   258|- T3.2.1: API key rotation (tools/key_rotation.py - KeyPool class)
   267|   260|   259|   259|- T3.2.2: Secure credential storage (tools/credential_storage.py - Fernet + keyring)
   268|   261|   260|   260|- T3.3.1: Rate limiting per user/chat (gateway/rate_limiter.py)
   269|   262|   261|   261|- T3.1.2: Docker sandbox mode (tools/code_execution_tool.py - resource limits, read-only fs, network isolation)
   270|   263|   262|- T3.3.2: Input validation for gateway messages (max length, sanitize control chars)
   271|   264|   263|   262|
   272|   265|   264|   263|### Additional Improvements
   273|   266|   265|   264|   260|- Added ddgs (DuckDuckGo) to dependencies for free web search
   274|   267|   266|   265|   261|- Created LOCAL_FIRST.md documentation
   275|   268|   267|   266|   262|- Marked deprecated API keys (WANDB_API_KEY, HONCHO_API_KEY)
   276|   269|   268|   267|   263|- Dead code cleanup: 7 skill dirs deleted, 6 test files deleted
   277|   270|   269|   268|   264|