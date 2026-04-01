# Aizen Agent — ACP (Agent Client Protocol) Setup Guide

Aizen Agent supports the **Agent Client Protocol (ACP)**, allowing it to run as
a coding agent inside your editor. ACP lets your IDE send tasks to Aizen, and
Aizen responds with file edits, terminal commands, and explanations — all shown
natively in the editor UI.

---

## Prerequisites

- Aizen Agent installed and configured (`aizen setup` completed)
- An API key / provider set up in `~/.aizen/.env` or via `aizen login`
- Python 3.11+

Install the ACP extra:

```bash
pip install -e ".[acp]"
```

---

## VS Code Setup

### 1. Install the ACP Client extension

Open VS Code and install **ACP Client** from the marketplace:

- Press `Ctrl+Shift+X` (or `Cmd+Shift+X` on macOS)
- Search for **"ACP Client"**
- Click **Install**

Or install from the command line:

```bash
code --install-extension anysphere.acp-client
```

### 2. Configure settings.json

Open your VS Code settings (`Ctrl+,` → click the `{}` icon for JSON) and add:

```json
{
  "acpClient.agents": [
    {
      "name": "aizen-agent",
      "registryDir": "/path/to/aizen-agent/acp_registry"
    }
  ]
}
```

Replace `/path/to/aizen-agent` with the actual path to your Aizen Agent
installation (e.g. `~/.aizen/aizen-agent`).

Alternatively, if `aizen` is on your PATH, the ACP Client can discover it
automatically via the registry directory.

### 3. Restart VS Code

After configuring, restart VS Code. You should see **Aizen Agent** appear in
the ACP agent picker in the chat/agent panel.

---

## Zed Setup

Zed has built-in ACP support.

### 1. Configure Zed settings

Open Zed settings (`Cmd+,` on macOS or `Ctrl+,` on Linux) and add to your
`settings.json`:

```json
{
  "acp": {
    "agents": [
      {
        "name": "aizen-agent",
        "registry_dir": "/path/to/aizen-agent/acp_registry"
      }
    ]
  }
}
```

### 2. Restart Zed

Aizen Agent will appear in the agent panel. Select it and start a conversation.

---

## JetBrains Setup (IntelliJ, PyCharm, WebStorm, etc.)

### 1. Install the ACP plugin

- Open **Settings** → **Plugins** → **Marketplace**
- Search for **"ACP"** or **"Agent Client Protocol"**
- Install and restart the IDE

### 2. Configure the agent

- Open **Settings** → **Tools** → **ACP Agents**
- Click **+** to add a new agent
- Set the registry directory to your `acp_registry/` folder:
  `/path/to/aizen-agent/acp_registry`
- Click **OK**

### 3. Use the agent

Open the ACP panel (usually in the right sidebar) and select **Aizen Agent**.

---

## What You Will See

Once connected, your editor provides a native interface to Aizen Agent:

### Chat Panel
A conversational interface where you can describe tasks, ask questions, and
give instructions. Aizen responds with explanations and actions.

### File Diffs
When Aizen edits files, you see standard diffs in the editor. You can:
- **Accept** individual changes
- **Reject** changes you don't want
- **Review** the full diff before applying

### Terminal Commands
When Aizen needs to run shell commands (builds, tests, installs), the editor
shows them in an integrated terminal. Depending on your settings:
- Commands may run automatically
- Or you may be prompted to **approve** each command

### Approval Flow
For potentially destructive operations, the editor will prompt you for
approval before Aizen proceeds. This includes:
- File deletions
- Shell commands
- Git operations

---

## Configuration

Aizen Agent under ACP uses the **same configuration** as the CLI:

- **API keys / providers**: `~/.aizen/.env`
- **Agent config**: `~/.aizen/config.yaml`
- **Skills**: `~/.aizen/skills/`
- **Sessions**: `~/.aizen/state.db`

You can run `aizen setup` to configure providers, or edit `~/.aizen/.env`
directly.

### Changing the model

Edit `~/.aizen/config.yaml`:

```yaml
model: openrouter/nous/aizen-3-llama-3.1-70b
```

Or set the `AIZEN_MODEL` environment variable.

### Toolsets

ACP sessions use the curated `aizen-acp` toolset by default. It is designed for editor workflows and intentionally excludes things like messaging delivery, cronjob management, and audio-first UX features.

---

## Troubleshooting

### Agent doesn't appear in the editor

1. **Check the registry path** — make sure the `acp_registry/` directory path
   in your editor settings is correct and contains `agent.json`.
2. **Check `aizen` is on PATH** — run `which aizen` in a terminal. If not
   found, you may need to activate your virtualenv or add it to PATH.
3. **Restart the editor** after changing settings.

### Agent starts but errors immediately

1. Run `aizen doctor` to check your configuration.
2. Check that you have a valid API key: `aizen status`
3. Try running `aizen acp` directly in a terminal to see error output.

### "Module not found" errors

Make sure you installed the ACP extra:

```bash
pip install -e ".[acp]"
```

### Slow responses

- ACP streams responses, so you should see incremental output. If the agent
  appears stuck, check your network connection and API provider status.
- Some providers have rate limits. Try switching to a different model/provider.

### Permission denied for terminal commands

If the editor blocks terminal commands, check your ACP Client extension
settings for auto-approval or manual-approval preferences.

### Logs

Aizen logs are written to stderr when running in ACP mode. Check:
- VS Code: **Output** panel → select **ACP Client** or **Aizen Agent**
- Zed: **View** → **Toggle Terminal** and check the process output
- JetBrains: **Event Log** or the ACP tool window

You can also enable verbose logging:

```bash
AIZEN_LOG_LEVEL=DEBUG aizen acp
```

---

## Further Reading

- [ACP Specification](https://github.com/anysphere/acp)
- [Aizen Agent Documentation](https://github.com/NousResearch/aizen-agent)
- Run `aizen --help` for all CLI options
