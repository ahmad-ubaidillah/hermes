     1|"""
     2|Configuration management for Aizen Agent.
     3|
     4|Config files are stored in ~/.aizen/ for easy access:
     5|- ~/.aizen/config.yaml  - All settings (model, toolsets, terminal, etc.)
     6|- ~/.aizen/.env         - API keys and secrets
     7|
     8|This module provides:
     9|- aizen config          - Show current configuration
    10|- aizen config edit     - Open config in editor
    11|- aizen config set      - Set a specific value
    12|- aizen config wizard   - Re-run setup wizard
    13|"""
    14|
    15|import os
    16|import platform
    17|import re
    18|import stat
    19|import subprocess
    20|import sys
    21|import tempfile
    22|from pathlib import Path
    23|from typing import Dict, Any, Optional, List, Tuple
    24|
    25|_IS_WINDOWS = platform.system() == "Windows"
    26|_ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    27|# Env var names written to .env that aren't in OPTIONAL_ENV_VARS
    28|# (managed by setup/provider flows directly).
    29|_EXTRA_ENV_KEYS = frozenset(
    30|    {
    31|        "OPENAI_API_KEY",
    32|        "OPENAI_BASE_URL",
    33|        "ANTHROPIC_API_KEY",
    34|        "ANTHROPIC_TOKEN",
    35|        "AUXILIARY_VISION_MODEL",
    36|        "DISCORD_HOME_CHANNEL",
    37|        "TELEGRAM_HOME_CHANNEL",
    38|        "SIGNAL_ACCOUNT",
    39|        "SIGNAL_HTTP_URL",
    40|        "SIGNAL_ALLOWED_USERS",
    41|        "SIGNAL_GROUP_ALLOWED_USERS",
    42|        "DINGTALK_CLIENT_ID",
    43|        "DINGTALK_CLIENT_SECRET",
    44|        "FEISHU_APP_ID",
    45|        "FEISHU_APP_SECRET",
    46|        "FEISHU_ENCRYPT_KEY",
    47|        "FEISHU_VERIFICATION_TOKEN",
    48|        "WECOM_BOT_ID",
    49|        "WECOM_SECRET",
    50|        "TERMINAL_ENV",
    51|        "TERMINAL_SSH_KEY",
    52|        "TERMINAL_SSH_PORT",
    53|        "WHATSAPP_MODE",
    54|        "WHATSAPP_ENABLED",
    55|        "MATTERMOST_HOME_CHANNEL",
    56|        "MATTERMOST_REPLY_MODE",
    57|        "MATRIX_PASSWORD",
    58|        "MATRIX_ENCRYPTION",
    59|        "MATRIX_HOME_ROOM",
    60|    }
    61|)
    62|
    63|import yaml
    64|
    65|from aizen_cli.colors import Colors, color
    66|from aizen_cli.default_soul import DEFAULT_SOUL_MD
    67|
    68|
    69|# =============================================================================
    70|# Managed mode (NixOS declarative config)
    71|# =============================================================================
    72|
    73|_MANAGED_TRUE_VALUES = ("true", "1", "yes")
    74|_MANAGED_SYSTEM_NAMES = {
    75|    "brew": "Homebrew",
    76|    "homebrew": "Homebrew",
    77|    "nix": "NixOS",
    78|    "nixos": "NixOS",
    79|}
    80|
    81|
    82|def get_managed_system() -> Optional[str]:
    83|    """Return the package manager owning this install, if any."""
    84|    raw = os.getenv("AIZEN_MANAGED", "").strip()
    85|    if raw:
    86|        normalized = raw.lower()
    87|        if normalized in _MANAGED_TRUE_VALUES:
    88|            return "NixOS"
    89|        return _MANAGED_SYSTEM_NAMES.get(normalized, raw)
    90|
    91|    managed_marker = get_aizen_home() / ".managed"
    92|    if managed_marker.exists():
    93|        return "NixOS"
    94|    return None
    95|
    96|
    97|def is_managed() -> bool:
    98|    """Check if Aizen is running in package-manager-managed mode.
    99|
   100|    Two signals: the AIZEN_MANAGED env var (set by the systemd service),
   101|    or a .managed marker file in AIZEN_HOME (set by the NixOS activation
   102|    script, so interactive shells also see it).
   103|    """
   104|    return get_managed_system() is not None
   105|
   106|
   107|def get_managed_update_command() -> Optional[str]:
   108|    """Return the preferred upgrade command for a managed install."""
   109|    managed_system = get_managed_system()
   110|    if managed_system == "Homebrew":
   111|        return "brew upgrade aizen-agent"
   112|    if managed_system == "NixOS":
   113|        return "sudo nixos-rebuild switch"
   114|    return None
   115|
   116|
   117|def recommended_update_command() -> str:
   118|    """Return the best update command for the current installation."""
   119|    return get_managed_update_command() or "aizen update"
   120|
   121|
   122|def format_managed_message(action: str = "modify this Aizen installation") -> str:
   123|    """Build a user-facing error for managed installs."""
   124|    managed_system = get_managed_system() or "a package manager"
   125|    raw = os.getenv("AIZEN_MANAGED", "").strip().lower()
   126|
   127|    if managed_system == "NixOS":
   128|        env_hint = "true" if raw in _MANAGED_TRUE_VALUES else raw or "true"
   129|        return (
   130|            f"Cannot {action}: this Aizen installation is managed by NixOS "
   131|            f"(AIZEN_MANAGED={env_hint}).\n"
   132|            "Edit services.aizen-agent.settings in your configuration.nix and run:\n"
   133|            "  sudo nixos-rebuild switch"
   134|        )
   135|
   136|    if managed_system == "Homebrew":
   137|        env_hint = raw or "homebrew"
   138|        return (
   139|            f"Cannot {action}: this Aizen installation is managed by Homebrew "
   140|            f"(AIZEN_MANAGED={env_hint}).\n"
   141|            "Use:\n"
   142|            "  brew upgrade aizen-agent"
   143|        )
   144|
   145|    return (
   146|        f"Cannot {action}: this Aizen installation is managed by {managed_system}.\n"
   147|        "Use your package manager to upgrade or reinstall Aizen."
   148|    )
   149|
   150|
   151|def managed_error(action: str = "modify configuration"):
   152|    """Print user-friendly error for managed mode."""
   153|    print(format_managed_message(action), file=sys.stderr)
   154|
   155|
   156|# =============================================================================
   157|# Config paths
   158|# =============================================================================
   159|
   160|# Re-export from aizen_constants — canonical definition lives there.
   161|from core.aizen_constants import get_aizen_home  # noqa: F811,E402
   162|
   163|
   164|def get_config_path() -> Path:
   165|    """Get the main config file path."""
   166|    return get_aizen_home() / "config.yaml"
   167|
   168|
   169|def get_env_path() -> Path:
   170|    """Get the .env file path (for API keys)."""
   171|    return get_aizen_home() / ".env"
   172|
   173|
   174|def get_project_root() -> Path:
   175|    """Get the project installation directory."""
   176|    return Path(__file__).parent.parent.resolve()
   177|
   178|
   179|def _secure_dir(path):
   180|    """Set directory to owner-only access (0700). No-op on Windows."""
   181|    try:
   182|        os.chmod(path, 0o700)
   183|    except (OSError, NotImplementedError):
   184|        pass
   185|
   186|
   187|def _secure_file(path):
   188|    """Set file to owner-only read/write (0600). No-op on Windows."""
   189|    try:
   190|        if os.path.exists(str(path)):
   191|            os.chmod(path, 0o600)
   192|    except (OSError, NotImplementedError):
   193|        pass
   194|
   195|
   196|def _ensure_default_soul_md(home: Path) -> None:
   197|    """Seed a default SOUL.md into AIZEN_HOME if the user doesn't have one yet."""
   198|    soul_path = home / "SOUL.md"
   199|    if soul_path.exists():
   200|        return
   201|    soul_path.write_text(DEFAULT_SOUL_MD, encoding="utf-8")
   202|    _secure_file(soul_path)
   203|
   204|
   205|def ensure_aizen_home():
   206|    """Ensure ~/.aizen directory structure exists with secure permissions."""
   207|    home = get_aizen_home()
   208|    home.mkdir(parents=True, exist_ok=True)
   209|    _secure_dir(home)
   210|    for subdir in ("cron", "sessions", "logs", "memories"):
   211|        d = home / subdir
   212|        d.mkdir(parents=True, exist_ok=True)
   213|        _secure_dir(d)
   214|    _ensure_default_soul_md(home)
   215|
   216|
   217|# =============================================================================
   218|# Config loading/saving
   219|# =============================================================================
   220|
   221|DEFAULT_CONFIG = {
   222|    "model": "anthropic/claude-opus-4.6",
   223|    "fallback_providers": [],
   224|    "toolsets": ["aizen-cli"],
   225|    "agent": {
   226|        "max_turns": 90,
   227|        # Tool-use enforcement: injects system prompt guidance that tells the
   228|        # model to actually call tools instead of describing intended actions.
   229|        # Values: "auto" (default — applies to gpt/codex models), true/false
   230|        # (force on/off for all models), or a list of model-name substrings
   231|        # to match (e.g. ["gpt", "codex", "gemini", "qwen"]).
   232|        "tool_use_enforcement": "auto",
   233|    },
   234|    "terminal": {
   235|        "backend": "local",
   236|        "cwd": ".",  # Use current directory
   237|        "timeout": 180,
   238|        # Environment variables to pass through to sandboxed execution
   239|        # (terminal and execute_code).  Skill-declared required_environment_variables
   240|        # are passed through automatically; this list is for non-skill use cases.
   241|        "env_passthrough": [],
   242|        "docker_image": "nikolaik/python-nodejs:python3.11-nodejs20",
   243|        "docker_forward_env": [],
   244|        "singularity_image": "docker://nikolaik/python-nodejs:python3.11-nodejs20",
   245|        "modal_image": "nikolaik/python-nodejs:python3.11-nodejs20",
   246|        "daytona_image": "nikolaik/python-nodejs:python3.11-nodejs20",
   247|        # Container resource limits (docker, singularity, modal, daytona — ignored for local/ssh)
   248|        "container_cpu": 1,
   249|        "container_memory": 5120,  # MB (default 5GB)
   250|        "container_disk": 51200,  # MB (default 50GB)
   251|        "container_persistent": True,  # Persist filesystem across sessions
   252|        # Docker volume mounts — share host directories with the container.
   253|        # Each entry is "host_path:container_path" (standard Docker -v syntax).
   254|        # Example: ["/home/user/projects:/workspace/projects", "/data:/data"]
   255|        "docker_volumes": [],
   256|        # Explicit opt-in: mount the host cwd into /workspace for Docker sessions.
   257|        # Default off because passing host directories into a sandbox weakens isolation.
   258|        "docker_mount_cwd_to_workspace": False,
   259|        # Persistent shell — keep a long-lived bash shell across execute() calls
   260|        # so cwd/env vars/shell variables survive between commands.
   261|        # Enabled by default for non-local backends (SSH); local is always opt-in
   262|        # via TERMINAL_LOCAL_PERSISTENT env var.
   263|        "persistent_shell": True,
   264|    },
   265|    "code_execution": {
   266|        "mode": "subprocess",
   267|        "timeout": 300,
   268|        "max_tool_calls": 50,
   269|        "docker_cpu": 0.5,
   270|        "docker_memory": "256m",
   271|        "docker_pids_limit": 64,
   272|        "docker_network": "none",
   273|        "docker_disk_read_bps": "10mb",
   274|        "docker_disk_write_bps": "10mb",
   275|        "docker_image": "python:3.11-slim",
   276|    },
   277|    "browser": {
   278|        "inactivity_timeout": 120,
   279|        "command_timeout": 30,  # Timeout for browser commands in seconds (screenshot, navigate, etc.)
   280|        "record_sessions": False,  # Auto-record browser sessions as WebM videos
   281|    },
   282|    # Filesystem checkpoints — automatic snapshots before destructive file ops.
   283|    # When enabled, the agent takes a snapshot of the working directory once per
   284|    # conversation turn (on first write_file/patch call).  Use /rollback to restore.
   285|    "checkpoints": {
   286|        "enabled": True,
   287|        "max_snapshots": 50,  # Max checkpoints to keep per directory
   288|    },
   289|    "compression": {
   290|        "enabled": True,
   291|        "threshold": 0.50,  # compress when context usage exceeds this ratio
   292|        "target_ratio": 0.20,  # fraction of threshold to preserve as recent tail
   293|        "protect_last_n": 20,  # minimum recent messages to keep uncompressed
   294|        "summary_model": "",  # empty = use main configured model
   295|        "summary_provider": "auto",
   296|        "summary_base_url": None,
   297|    },
   298|    "smart_model_routing": {
   299|        "enabled": False,
   300|        "max_simple_chars": 160,
   301|        "max_simple_words": 28,
   302|        "cheap_model": {},
   303|    },
   304|    # Auxiliary model config — provider:model for each side task.
   305|    # Format: provider is the provider name, model is the model slug.
   306|    # "auto" for provider = auto-detect best available provider.
   307|    # Empty model = use provider's default auxiliary model.
   308|    # All tasks fall back to openrouter:google/gemini-3-flash-preview if
   309|    # the configured provider is unavailable.
   310|    "auxiliary": {
   311|        "vision": {
   312|            "provider": "auto",  # auto | openrouter | nous | codex | custom
   313|            "model": "",  # e.g. "google/gemini-2.5-flash", "gpt-4o"
   314|            "base_url": "",  # direct OpenAI-compatible endpoint (takes precedence over provider)
   315|            "api_key": "",  # API key for base_url (falls back to OPENAI_API_KEY)
   316|            "timeout": 30,  # seconds — LLM API call timeout; increase for slow local vision models
   317|            "download_timeout": 30,  # seconds — image HTTP download timeout; increase for slow connections
   318|        },
   319|        "web_extract": {
   320|            "provider": "auto",
   321|            "model": "",
   322|            "base_url": "",
   323|            "api_key": "",
   324|            "timeout": 30,  # seconds — increase for slow local models
   325|        },
   326|        "compression": {
   327|            "provider": "auto",
   328|            "model": "",
   329|            "base_url": "",
   330|            "api_key": "",
   331|            "timeout": 120,  # seconds — compression summarises large contexts; increase for local models
   332|        },
   333|        "session_search": {
   334|            "provider": "auto",
   335|            "model": "",
   336|            "base_url": "",
   337|            "api_key": "",
   338|            "timeout": 30,
   339|        },
   340|        "skills_hub": {
   341|            "provider": "auto",
   342|            "model": "",
   343|            "base_url": "",
   344|            "api_key": "",
   345|            "timeout": 30,
   346|        },
   347|        "approval": {
   348|            "provider": "auto",
   349|            "model": "",  # fast/cheap model recommended (e.g. gemini-flash, haiku)
   350|            "base_url": "",
   351|            "api_key": "",
   352|            "timeout": 30,
   353|        },
   354|        "mcp": {
   355|            "provider": "auto",
   356|            "model": "",
   357|            "base_url": "",
   358|            "api_key": "",
   359|            "timeout": 30,
   360|        },
   361|        "flush_memories": {
   362|            "provider": "auto",
   363|            "model": "",
   364|            "base_url": "",
   365|            "api_key": "",
   366|            "timeout": 30,
   367|        },
   368|    },
   369|    "display": {
   370|        "compact": False,
   371|        "personality": "kawaii",
   372|        "resume_display": "full",
   373|        "busy_input_mode": "interrupt",
   374|        "bell_on_complete": False,
   375|        "show_reasoning": False,
   376|        "streaming": False,
   377|        "show_cost": False,  # Show $ cost in the status bar (off by default)
   378|        "skin": "default",
   379|        "tool_progress_command": False,  # Enable /verbose command in messaging gateway
   380|        "tool_preview_length": 0,  # Max chars for tool call previews (0 = no limit, show full paths/commands)
   381|    },
   382|    # Privacy settings
   383|    "privacy": {
   384|        "redact_pii": False,  # When True, hash user IDs and strip phone numbers from LLM context
   385|    },
   386|    # Text-to-speech configuration
   387|    "tts": {
   388|        "provider": "edge",  # "edge" (free) | "elevenlabs" (premium) | "openai" | "neutts" (local)
   389|        "edge": {
   390|            "voice": "en-US-AriaNeural",
   391|            # Popular: AriaNeural, JennyNeural, AndrewNeural, BrianNeural, SoniaNeural
   392|        },
   393|        "elevenlabs": {
   394|            "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam
   395|            "model_id": "eleven_multilingual_v2",
   396|        },
   397|        "openai": {
   398|            "model": "gpt-4o-mini-tts",
   399|            "voice": "alloy",
   400|            # Voices: alloy, echo, fable, onyx, nova, shimmer
   401|        },
   402|        "neutts": {
   403|            "ref_audio": "",  # Path to reference voice audio (empty = bundled default)
   404|            "ref_text": "",  # Path to reference voice transcript (empty = bundled default)
   405|            "model": "neuphonic/neutts-air-q4-gguf",  # HuggingFace model repo
   406|            "device": "cpu",  # cpu, cuda, or mps
   407|        },
   408|    },
   409|    "stt": {
   410|        "enabled": True,
   411|        "provider": "local",  # "local" (free, faster-whisper) | "groq" | "openai" (Whisper API)
   412|        "local": {
   413|            "model": "base",  # tiny, base, small, medium, large-v3
   414|        },
   415|        "openai": {
   416|            "model": "whisper-1",  # whisper-1, gpt-4o-mini-transcribe, gpt-4o-transcribe
   417|        },
   418|    },
   419|    "voice": {
   420|        "record_key": "ctrl+b",
   421|        "max_recording_seconds": 120,
   422|        "auto_tts": False,
   423|        "silence_threshold": 200,  # RMS below this = silence (0-32767)
   424|        "silence_duration": 3.0,  # Seconds of silence before auto-stop
   425|    },
   426|    "human_delay": {
   427|        "mode": "off",
   428|        "min_ms": 800,
   429|        "max_ms": 2500,
   430|    },
   431|    # Persistent memory -- bounded curated memory injected into system prompt
   432|    "memory": {
   433|        "memory_enabled": True,
   434|        "user_profile_enabled": True,
   435|        "memory_char_limit": 2200,  # ~800 tokens at 2.75 chars/token
   436|        "user_char_limit": 1375,  # ~500 tokens at 2.75 chars/token
   437|    },
   438|    # Subagent delegation — override the provider:model used by delegate_task
   439|    # so child agents can run on a different (cheaper/faster) provider and model.
   440|    # Uses the same runtime provider resolution as CLI/gateway startup, so all
   441|    # configured providers (OpenRouter, Nous, Z.ai, Kimi, etc.) are supported.
   442|    "delegation": {
   443|        "model": "",  # e.g. "google/gemini-3-flash-preview" (empty = inherit parent model)
   444|        "provider": "",  # e.g. "openrouter" (empty = inherit parent provider + credentials)
   445|        "base_url": "",  # direct OpenAI-compatible endpoint for subagents
   446|        "api_key": "",  # API key for delegation.base_url (falls back to OPENAI_API_KEY)
   447|        "max_iterations": 50,  # per-subagent iteration cap (each subagent gets its own budget,
   448|        # independent of the parent's max_iterations)
   449|    },
   450|    # Ephemeral prefill messages file — JSON list of {role, content} dicts
   451|    # injected at the start of every API call for few-shot priming.
   452|    # Never saved to sessions, logs, or trajectories.
   453|    "prefill_messages_file": "",
   454|    # Skills — external skill directories for sharing skills across tools/agents.
   455|    # Each path is expanded (~, ${VAR}) and resolved.  Read-only — skill creation
   456|    # always goes to ~/.aizen/skills/.
   457|    "skills": {
   458|        "external_dirs": [],  # e.g. ["~/.agents/skills", "/shared/team-skills"]
   459|    },
   460|    # Honcho AI-native memory -- reads ~/.honcho/config.json as single source of truth.
   461|    # This section is only needed for aizen-specific overrides; everything else
   462|    # (apiKey, workspace, peerName, sessions, enabled) comes from the global config.
   463|    "honcho": {},
   464|    # IANA timezone (e.g. "Asia/Kolkata", "America/New_York").
   465|    # Empty string means use server-local time.
   466|    "timezone": "",
   467|    # Discord platform settings (gateway mode)
   468|    "discord": {
   469|        "require_mention": True,  # Require @mention to respond in server channels
   470|        "free_response_channels": "",  # Comma-separated channel IDs where bot responds without mention
   471|        "auto_thread": True,  # Auto-create threads on @mention in channels (like Slack)
   472|    },
   473|    # WhatsApp platform settings (gateway mode)
   474|    "whatsapp": {
   475|        # Reply prefix prepended to every outgoing WhatsApp message.
   476|        # Default (None) uses the built-in "⚕ *Aizen Agent*" header.
   477|        # Set to "" (empty string) to disable the header entirely.
   478|        # Supports \n for newlines, e.g. "🤖 *My Bot*\n──────\n"
   479|    },
   480|    # Approval mode for dangerous commands:
   481|    #   manual — always prompt the user (default)
   482|    #   smart  — use auxiliary LLM to auto-approve low-risk commands, prompt for high-risk
   483|    #   off    — skip all approval prompts (equivalent to --yolo)
   484|    "approvals": {
   485|        "mode": "manual",
   486|        "timeout": 60,
   487|    },
   488|    # Permanently allowed dangerous command patterns (added via "always" approval)
   489|    "command_allowlist": [],
   490|    # User-defined quick commands that bypass the agent loop (type: exec only)
   491|    "quick_commands": {},
   492|    # Custom personalities — add your own entries here
   493|    # Supports string format: {"name": "system prompt"}
   494|    # Or dict format: {"name": {"description": "...", "system_prompt": "...", "tone": "...", "style": "..."}}
   495|    "personalities": {},
   496|    # Pre-exec security scanning via tirith
   497|    "security": {
   498|        "redact_secrets": True,
   499|        "tirith_enabled": True,
   500|        "tirith_path": "tirith",
   501|