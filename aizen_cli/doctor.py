     1|"""
     2|Doctor command for aizen CLI.
     3|
     4|Diagnoses issues with Aizen Agent setup.
     5|"""
     6|
     7|import os
     8|import sys
     9|import subprocess
    10|import shutil
    11|
    12|from aizen_cli.config import get_project_root, get_aizen_home, get_env_path
    13|from core.aizen_constants import display_aizen_home
    14|
    15|PROJECT_ROOT = get_project_root()
    16|AIZEN_HOME = get_aizen_home()
    17|_DHH = display_aizen_home()  # user-facing display path (e.g. ~/.aizen or ~/.aizen/profiles/coder)
    18|
    19|# Load environment variables from ~/.aizen/.env so API key checks work
    20|from dotenv import load_dotenv
    21|_env_path = get_env_path()
    22|if _env_path.exists():
    23|    try:
    24|        load_dotenv(_env_path, encoding="utf-8")
    25|    except UnicodeDecodeError:
    26|        load_dotenv(_env_path, encoding="latin-1")
    27|# Also try project .env as dev fallback
    28|load_dotenv(PROJECT_ROOT / ".env", override=False, encoding="utf-8")
    29|
    30|from aizen_cli.colors import Colors, color
    31|from core.aizen_constants import OPENROUTER_MODELS_URL
    32|
    33|
    34|_PROVIDER_ENV_HINTS = (
    35|    "OPENROUTER_API_KEY",
    36|    "OPENAI_API_KEY",
    37|    "ANTHROPIC_API_KEY",
    38|    "ANTHROPIC_TOKEN",
    39|    "OPENAI_BASE_URL",
    40|    "GLM_API_KEY",
    41|    "ZAI_API_KEY",
    42|    "Z_AI_API_KEY",
    43|    "KIMI_API_KEY",
    44|    "MINIMAX_API_KEY",
    45|    "MINIMAX_CN_API_KEY",
    46|    "KILOCODE_API_KEY",
    47|)
    48|
    49|
    50|def _has_provider_env_config(content: str) -> bool:
    51|    """Return True when ~/.aizen/.env contains provider auth/base URL settings."""
    52|    return any(key in content for key in _PROVIDER_ENV_HINTS)
    53|
    54|
    80|
    81|
    82|def check_ok(text: str, detail: str = ""):
    83|    print(f"  {color('✓', Colors.GREEN)} {text}" + (f" {color(detail, Colors.DIM)}" if detail else ""))
    84|
    85|def check_warn(text: str, detail: str = ""):
    86|    print(f"  {color('⚠', Colors.YELLOW)} {text}" + (f" {color(detail, Colors.DIM)}" if detail else ""))
    87|
    88|def check_fail(text: str, detail: str = ""):
    89|    print(f"  {color('✗', Colors.RED)} {text}" + (f" {color(detail, Colors.DIM)}" if detail else ""))
    90|
    91|def check_info(text: str):
    92|    print(f"    {color('→', Colors.CYAN)} {text}")
    93|
    94|
    95|def _check_gateway_service_linger(issues: list[str]) -> None:
    96|    """Warn when a systemd user gateway service will stop after logout."""
    97|    try:
    98|        from aizen_cli.gateway import (
    99|            get_systemd_linger_status,
   100|            get_systemd_unit_path,
   101|            is_linux,
   102|        )
   103|    except Exception as e:
   104|        check_warn("Gateway service linger", f"(could not import gateway helpers: {e})")
   105|        return
   106|
   107|    if not is_linux():
   108|        return
   109|
   110|    unit_path = get_systemd_unit_path()
   111|    if not unit_path.exists():
   112|        return
   113|
   114|    print()
   115|    print(color("◆ Gateway Service", Colors.CYAN, Colors.BOLD))
   116|
   117|    linger_enabled, linger_detail = get_systemd_linger_status()
   118|    if linger_enabled is True:
   119|        check_ok("Systemd linger enabled", "(gateway service survives logout)")
   120|    elif linger_enabled is False:
   121|        check_warn("Systemd linger disabled", "(gateway may stop after logout)")
   122|        check_info("Run: sudo loginctl enable-linger $USER")
   123|        issues.append("Enable linger for the gateway user service: sudo loginctl enable-linger $USER")
   124|    else:
   125|        check_warn("Could not verify systemd linger", f"({linger_detail})")
   126|
   127|
   128|def run_doctor(args):
   129|    """Run diagnostic checks."""
   130|    should_fix = getattr(args, 'fix', False)
   131|
   132|    # Doctor runs from the interactive CLI, so CLI-gated tool availability
   133|    # checks (like cronjob management) should see the same context as `aizen`.
   134|    os.environ.setdefault("AIZEN_INTERACTIVE", "1")
   135|    
   136|    issues = []
   137|    manual_issues = []  # issues that can't be auto-fixed
   138|    fixed_count = 0
   139|    
   140|    print()
   141|    print(color("┌─────────────────────────────────────────────────────────┐", Colors.CYAN))
   142|    print(color("│                 🩺 Aizen Doctor                        │", Colors.CYAN))
   143|    print(color("└─────────────────────────────────────────────────────────┘", Colors.CYAN))
   144|    
   145|    # =========================================================================
   146|    # Check: Python version
   147|    # =========================================================================
   148|    print()
   149|    print(color("◆ Python Environment", Colors.CYAN, Colors.BOLD))
   150|    
   151|    py_version = sys.version_info
   152|    if py_version >= (3, 11):
   153|        check_ok(f"Python {py_version.major}.{py_version.minor}.{py_version.micro}")
   154|    elif py_version >= (3, 10):
   155|        check_ok(f"Python {py_version.major}.{py_version.minor}.{py_version.micro}")
   156|        check_warn("Python 3.11+ recommended for RL Training tools (tinker requires >= 3.11)")
   157|    elif py_version >= (3, 8):
   158|        check_warn(f"Python {py_version.major}.{py_version.minor}.{py_version.micro}", "(3.10+ recommended)")
   159|    else:
   160|        check_fail(f"Python {py_version.major}.{py_version.minor}.{py_version.micro}", "(3.10+ required)")
   161|        issues.append("Upgrade Python to 3.10+")
   162|    
   163|    # Check if in virtual environment
   164|    in_venv = sys.prefix != sys.base_prefix
   165|    if in_venv:
   166|        check_ok("Virtual environment active")
   167|    else:
   168|        check_warn("Not in virtual environment", "(recommended)")
   169|    
   170|    # =========================================================================
   171|    # Check: Required packages
   172|    # =========================================================================
   173|    print()
   174|    print(color("◆ Required Packages", Colors.CYAN, Colors.BOLD))
   175|    
   176|    required_packages = [
   177|        ("openai", "OpenAI SDK"),
   178|        ("rich", "Rich (terminal UI)"),
   179|        ("dotenv", "python-dotenv"),
   180|        ("yaml", "PyYAML"),
   181|        ("httpx", "HTTPX"),
   182|    ]
   183|    
   184|    optional_packages = [
   185|        ("croniter", "Croniter (cron expressions)"),
   186|        ("telegram", "python-telegram-bot"),
   187|        ("discord", "discord.py"),
   188|    ]
   189|    
   190|    for module, name in required_packages:
   191|        try:
   192|            __import__(module)
   193|            check_ok(name)
   194|        except ImportError:
   195|            check_fail(name, "(missing)")
   196|            issues.append(f"Install {name}: uv pip install {module}")
   197|    
   198|    for module, name in optional_packages:
   199|        try:
   200|            __import__(module)
   201|            check_ok(name, "(optional)")
   202|        except ImportError:
   203|            check_warn(name, "(optional, not installed)")
   204|    
   205|    # =========================================================================
   206|    # Check: Configuration files
   207|    # =========================================================================
   208|    print()
   209|    print(color("◆ Configuration Files", Colors.CYAN, Colors.BOLD))
   210|    
   211|    # Check ~/.aizen/.env (primary location for user config)
   212|    env_path = AIZEN_HOME / '.env'
   213|    if env_path.exists():
   214|        check_ok(f"{_DHH}/.env file exists")
   215|        
   216|        # Check for common issues
   217|        content = env_path.read_text()
   218|        if _has_provider_env_config(content):
   219|            check_ok("API key or custom endpoint configured")
   220|        else:
   221|            check_warn(f"No API key found in {_DHH}/.env")
   222|            issues.append("Run 'aizen setup' to configure API keys")
   223|    else:
   224|        # Also check project root as fallback
   225|        fallback_env = PROJECT_ROOT / '.env'
   226|        if fallback_env.exists():
   227|            check_ok(".env file exists (in project directory)")
   228|        else:
   229|            check_fail(f"{_DHH}/.env file missing")
   230|            if should_fix:
   231|                env_path.parent.mkdir(parents=True, exist_ok=True)
   232|                env_path.touch()
   233|                check_ok(f"Created empty {_DHH}/.env")
   234|                check_info("Run 'aizen setup' to configure API keys")
   235|                fixed_count += 1
   236|            else:
   237|                check_info("Run 'aizen setup' to create one")
   238|                issues.append("Run 'aizen setup' to create .env")
   239|    
   240|    # Check ~/.aizen/config.yaml (primary) or project cli-config.yaml (fallback)
   241|    config_path = AIZEN_HOME / 'config.yaml'
   242|    if config_path.exists():
   243|        check_ok(f"{_DHH}/config.yaml exists")
   244|    else:
   245|        fallback_config = PROJECT_ROOT / 'cli-config.yaml'
   246|        if fallback_config.exists():
   247|            check_ok("cli-config.yaml exists (in project directory)")
   248|        else:
   249|            example_config = PROJECT_ROOT / 'cli-config.yaml.example'
   250|            if should_fix and example_config.exists():
   251|                config_path.parent.mkdir(parents=True, exist_ok=True)
   252|                shutil.copy2(str(example_config), str(config_path))
   253|                check_ok(f"Created {_DHH}/config.yaml from cli-config.yaml.example")
   254|                fixed_count += 1
   255|            elif should_fix:
   256|                check_warn("config.yaml not found and no example to copy from")
   257|                manual_issues.append(f"Create {_DHH}/config.yaml manually")
   258|            else:
   259|                check_warn("config.yaml not found", "(using defaults)")
   260|    
   261|    # =========================================================================
   262|    # Check: Auth providers
   263|    # =========================================================================
   264|    print()
   265|    print(color("◆ Auth Providers", Colors.CYAN, Colors.BOLD))
   266|
   267|    try:
   268|        from aizen_cli.auth import get_nous_auth_status, get_codex_auth_status
   269|
   270|        nous_status = get_nous_auth_status()
   271|        if nous_status.get("logged_in"):
   272|            check_ok("Nous Portal auth", "(logged in)")
   273|        else:
   274|            check_warn("Nous Portal auth", "(not logged in)")
   275|
   276|        codex_status = get_codex_auth_status()
   277|        if codex_status.get("logged_in"):
   278|            check_ok("OpenAI Codex auth", "(logged in)")
   279|        else:
   280|            check_warn("OpenAI Codex auth", "(not logged in)")
   281|            if codex_status.get("error"):
   282|                check_info(codex_status["error"])
   283|    except Exception as e:
   284|        check_warn("Auth provider status", f"(could not check: {e})")
   285|
   286|    if shutil.which("codex"):
   287|        check_ok("codex CLI")
   288|    else:
   289|        check_warn("codex CLI not found", "(required for openai-codex login)")
   290|
   291|    # =========================================================================
   292|    # Check: Directory structure
   293|    # =========================================================================
   294|    print()
   295|    print(color("◆ Directory Structure", Colors.CYAN, Colors.BOLD))
   296|    
   297|    aizen_home = AIZEN_HOME
   298|    if aizen_home.exists():
   299|        check_ok(f"{_DHH} directory exists")
   300|    else:
   301|        if should_fix:
   302|            aizen_home.mkdir(parents=True, exist_ok=True)
   303|            check_ok(f"Created {_DHH} directory")
   304|            fixed_count += 1
   305|        else:
   306|            check_warn(f"{_DHH} not found", "(will be created on first use)")
   307|    
   308|    # Check expected subdirectories
   309|    expected_subdirs = ["cron", "sessions", "logs", "skills", "memories"]
   310|    for subdir_name in expected_subdirs:
   311|        subdir_path = aizen_home / subdir_name
   312|        if subdir_path.exists():
   313|            check_ok(f"{_DHH}/{subdir_name}/ exists")
   314|        else:
   315|            if should_fix:
   316|                subdir_path.mkdir(parents=True, exist_ok=True)
   317|                check_ok(f"Created {_DHH}/{subdir_name}/")
   318|                fixed_count += 1
   319|            else:
   320|                check_warn(f"{_DHH}/{subdir_name}/ not found", "(will be created on first use)")
   321|    
   322|    # Check for SOUL.md persona file
   323|    soul_path = aizen_home / "SOUL.md"
   324|    if soul_path.exists():
   325|        content = soul_path.read_text(encoding="utf-8").strip()
   326|        # Check if it's just the template comments (no real content)
   327|        lines = [l for l in content.splitlines() if l.strip() and not l.strip().startswith(("<!--", "-->", "#"))]
   328|        if lines:
   329|            check_ok(f"{_DHH}/SOUL.md exists (persona configured)")
   330|        else:
   331|            check_info(f"{_DHH}/SOUL.md exists but is empty — edit it to customize personality")
   332|    else:
   333|        check_warn(f"{_DHH}/SOUL.md not found", "(create it to give Aizen a custom personality)")
   334|        if should_fix:
   335|            soul_path.parent.mkdir(parents=True, exist_ok=True)
   336|            soul_path.write_text(
   337|                "# Aizen Agent Persona\n\n"
   338|                "<!-- Edit this file to customize how Aizen communicates. -->\n\n"
   339|                "You are Aizen, a helpful AI assistant.\n",
   340|                encoding="utf-8",
   341|            )
   342|            check_ok(f"Created {_DHH}/SOUL.md with basic template")
   343|            fixed_count += 1
   344|    
   345|    # Check memory directory
   346|    memories_dir = aizen_home / "memories"
   347|    if memories_dir.exists():
   348|        check_ok(f"{_DHH}/memories/ directory exists")
   349|        memory_file = memories_dir / "MEMORY.md"
   350|        user_file = memories_dir / "USER.md"
   351|        if memory_file.exists():
   352|            size = len(memory_file.read_text(encoding="utf-8").strip())
   353|            check_ok(f"MEMORY.md exists ({size} chars)")
   354|        else:
   355|            check_info("MEMORY.md not created yet (will be created when the agent first writes a memory)")
   356|        if user_file.exists():
   357|            size = len(user_file.read_text(encoding="utf-8").strip())
   358|            check_ok(f"USER.md exists ({size} chars)")
   359|        else:
   360|            check_info("USER.md not created yet (will be created when the agent first writes a memory)")
   361|    else:
   362|        check_warn(f"{_DHH}/memories/ not found", "(will be created on first use)")
   363|        if should_fix:
   364|            memories_dir.mkdir(parents=True, exist_ok=True)
   365|            check_ok(f"Created {_DHH}/memories/")
   366|            fixed_count += 1
   367|    
   368|    # Check SQLite session store
   369|    state_db_path = aizen_home / "state.db"
   370|    if state_db_path.exists():
   371|        try:
   372|            import sqlite3
   373|            conn = sqlite3.connect(str(state_db_path))
   374|            cursor = conn.execute("SELECT COUNT(*) FROM sessions")
   375|            count = cursor.fetchone()[0]
   376|            conn.close()
   377|            check_ok(f"{_DHH}/state.db exists ({count} sessions)")
   378|        except Exception as e:
   379|            check_warn(f"{_DHH}/state.db exists but has issues: {e}")
   380|    else:
   381|        check_info(f"{_DHH}/state.db not created yet (will be created on first session)")
   382|
   383|    _check_gateway_service_linger(issues)
   384|    
   385|    # =========================================================================
   386|    # Check: External tools
   387|    # =========================================================================
   388|    print()
   389|    print(color("◆ External Tools", Colors.CYAN, Colors.BOLD))
   390|    
   391|    # Git
   392|    if shutil.which("git"):
   393|        check_ok("git")
   394|    else:
   395|        check_warn("git not found", "(optional)")
   396|    
   397|    # ripgrep (optional, for faster file search)
   398|    if shutil.which("rg"):
   399|        check_ok("ripgrep (rg)", "(faster file search)")
   400|    else:
   401|        check_warn("ripgrep (rg) not found", "(file search uses grep fallback)")
   402|        check_info("Install for faster search: sudo apt install ripgrep")
   403|    
   404|    # Docker (optional)
   405|    terminal_env = os.getenv("TERMINAL_ENV", "local")
   406|    if terminal_env == "docker":
   407|        if shutil.which("docker"):
   408|            # Check if docker daemon is running
   409|            try:
   410|                result = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
   411|            except subprocess.TimeoutExpired:
   412|                result = None
   413|            if result is not None and result.returncode == 0:
   414|                check_ok("docker", "(daemon running)")
   415|            else:
   416|                check_fail("docker daemon not running")
   417|                issues.append("Start Docker daemon")
   418|        else:
   419|            check_fail("docker not found", "(required for TERMINAL_ENV=docker)")
   420|            issues.append("Install Docker or change TERMINAL_ENV")
   421|    else:
   422|        if shutil.which("docker"):
   423|            check_ok("docker", "(optional)")
   424|        else:
   425|            check_warn("docker not found", "(optional)")
   426|    
   427|    # SSH (if using ssh backend)
   428|    if terminal_env == "ssh":
   429|        ssh_host = os.getenv("TERMINAL_SSH_HOST")
   430|        if ssh_host:
   431|            # Try to connect
   432|            try:
   433|                result = subprocess.run(
   434|                    ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", ssh_host, "echo ok"],
   435|                    capture_output=True,
   436|                    text=True,
   437|                    timeout=15
   438|                )
   439|            except subprocess.TimeoutExpired:
   440|                result = None
   441|            if result is not None and result.returncode == 0:
   442|                check_ok(f"SSH connection to {ssh_host}")
   443|            else:
   444|                check_fail(f"SSH connection to {ssh_host}")
   445|                issues.append(f"Check SSH configuration for {ssh_host}")
   446|        else:
   447|            check_fail("TERMINAL_SSH_HOST not set", "(required for TERMINAL_ENV=ssh)")
   448|            issues.append("Set TERMINAL_SSH_HOST in .env")
   449|    
   450|    # Daytona (if using daytona backend)
   451|    if terminal_env == "daytona":
   452|        daytona_key = os.getenv("DAYTONA_API_KEY")
   453|        if daytona_key:
   454|            check_ok("Daytona API key", "(configured)")
   455|        else:
   456|            check_fail("DAYTONA_API_KEY not set", "(required for TERMINAL_ENV=daytona)")
   457|            issues.append("Set DAYTONA_API_KEY environment variable")
   458|        try:
   459|            from daytona import Daytona  # noqa: F401 — SDK presence check
   460|            check_ok("daytona SDK", "(installed)")
   461|        except ImportError:
   462|            check_fail("daytona SDK not installed", "(pip install daytona)")
   463|            issues.append("Install daytona SDK: pip install daytona")
   464|
   465|    # Node.js + agent-browser (for browser automation tools)
   466|    if shutil.which("node"):
   467|        check_ok("Node.js")
   468|        # Check if agent-browser is installed
   469|        agent_browser_path = PROJECT_ROOT / "node_modules" / "agent-browser"
   470|        if agent_browser_path.exists():
   471|            check_ok("agent-browser (Node.js)", "(browser automation)")
   472|        else:
   473|            check_warn("agent-browser not installed", "(run: npm install)")
   474|    else:
   475|        check_warn("Node.js not found", "(optional, needed for browser tools)")
   476|    
   477|    # npm audit for all Node.js packages
   478|    if shutil.which("npm"):
   479|        npm_dirs = [
   480|            (PROJECT_ROOT, "Browser tools (agent-browser)"),
   481|            (PROJECT_ROOT / "scripts" / "whatsapp-bridge", "WhatsApp bridge"),
   482|        ]
   483|        for npm_dir, label in npm_dirs:
   484|            if not (npm_dir / "node_modules").exists():
   485|                continue
   486|            try:
   487|                audit_result = subprocess.run(
   488|                    ["npm", "audit", "--json"],
   489|                    cwd=str(npm_dir),
   490|                    capture_output=True, text=True, timeout=30,
   491|                )
   492|                import json as _json
   493|                audit_data = _json.loads(audit_result.stdout) if audit_result.stdout.strip() else {}
   494|                vuln_count = audit_data.get("metadata", {}).get("vulnerabilities", {})
   495|                critical = vuln_count.get("critical", 0)
   496|                high = vuln_count.get("high", 0)
   497|                moderate = vuln_count.get("moderate", 0)
   498|                total = critical + high + moderate
   499|                if total == 0:
   500|                    check_ok(f"{label} deps", "(no known vulnerabilities)")
   501|