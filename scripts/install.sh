#!/bin/bash
# ============================================================================
# Aizen Agent - One-Line Installer
# ============================================================================
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/aizen/main/scripts/install.sh | bash
#
# Options:
#   --skip-setup      Skip setup wizard
#   --no-opencode     Skip OpenCode check
#   --minimal         Minimal install
#   --branch NAME     Install specific branch
#
# ============================================================================

set -e

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[0;33m'; C='\033[0;36m'; B='\033[1m'; N='\033[0m'

# Parse args
RUN_SETUP=true
CHECK_OPENCODE=true
MINIMAL=false
BRANCH="main"
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup) RUN_SETUP=false; shift ;;
        --no-opencode) CHECK_OPENCODE=false; shift ;;
        --minimal) MINIMAL=true; CHECK_OPENCODE=false; shift ;;
        --branch) BRANCH="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Banner
echo -e "${C}${B}"
echo "  ⚕ Aizen Agent Installer"
echo "  Execute with Zen"
echo -e "${N}"

# OS check
OS="$(uname -s)"
[[ "$OS" != "Linux" && "$OS" != "Darwin" ]] && { echo -e "${R}Unsupported OS${N}"; exit 1; }

# Config
INSTALL_DIR="$HOME/.aizen/aizen-agent"

# Step 1: Install uv
echo -e "${C}▸ Installing uv...${N}"
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    export PATH="$HOME/.local/bin:$PATH"
fi
echo -e "${G}✓ uv ready${N}"

# Step 2: Clone/Update repository
echo -e "${C}▸ Installing Aizen...${N}"
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR" && git pull origin "$BRANCH" >/dev/null 2>&1 || true
else
    git clone -b "$BRANCH" https://github.com/ahmad-ubaidillah/aizen.git "$INSTALL_DIR" >/dev/null 2>&1
    cd "$INSTALL_DIR"
fi
echo -e "${G}✓ Repository ready${N}"

# Step 3: Setup Python environment
echo -e "${C}▸ Setting up Python environment...${N}"
rm -rf "$INSTALL_DIR/venv" "$INSTALL_DIR/.venv"
uv venv venv --python 3.11 >/dev/null 2>&1
source venv/bin/activate
echo -e "${C}▸ Installing packages...${N}"
uv pip install -e ".[all]" >/dev/null 2>&1 || uv pip install -e "." >/dev/null 2>&1
echo -e "${G}✓ Environment ready${N}"

# Step 4: Check & Install OpenCode
if [ "$CHECK_OPENCODE" = true ]; then
    echo -e "${C}▸ Checking OpenCode...${N}"
    if ! command -v opencode &>/dev/null; then
        echo -e "${Y}  OpenCode not found. Installing...${N}"
        if command -v npm &>/dev/null; then
            npm install -g @opencode-ai/opencode >/dev/null 2>&1 && \
                echo -e "${G}✓ OpenCode installed${N}" || \
                echo -e "${Y}⚠ OpenCode install failed (optional)${N}"
        else
            echo -e "${Y}⚠ npm not found, skipping OpenCode${N}"
        fi
    else
        echo -e "${G}✓ OpenCode found${N}"
    fi
fi

# Step 5: Create config directory
mkdir -p "$HOME/.aizen"

# Step 6: Create aizen command
echo -e "${C}▸ Creating aizen command...${N}"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/aizen" << 'CMD'
#!/bin/bash
# Aizen CLI - Auto-detects credentials from OpenCode if available
# NEVER hardcodes API keys - respects user privacy

# Try to detect OpenCode Z.AI credentials (optional convenience)
if [ -z "$ZAI_API_KEY" ] && [ -f "$HOME/.local/share/opencode/auth.json" ]; then
    ZAI_KEY=$(python3 -c "import json; d=json.load(open('$HOME/.local/share/opencode/auth.json')); print(d.get('zai-coding-plan',{}).get('key',''))" 2>/dev/null)
    [ -n "$ZAI_KEY" ] && export ZAI_API_KEY="$ZAI_KEY"
fi

# Source .env if exists (user's own config)
[ -f "$HOME/.aizen/.env" ] && export $(grep -v '^#' "$HOME/.aizen/.env" | xargs 2>/dev/null || true)

# Activate and run
source "$HOME/.aizen/aizen-agent/venv/bin/activate"
python "$HOME/.aizen/aizen-agent/cli.py" "$@"
CMD
chmod +x "$HOME/.local/bin/aizen"
echo -e "${G}✓ Command created${N}"

# Step 7: Add to PATH
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc" ] && ! grep -q '\.local/bin' "$rc" 2>/dev/null; then
        echo "" >> "$rc"
        echo "# Aizen Agent" >> "$rc"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
    fi
done
export PATH="$HOME/.local/bin:$PATH"
echo -e "${G}✓ Added to PATH${N}"

# Step 8: Create default config
if [ ! -f "$HOME/.aizen/config.yaml" ]; then
    cat > "$HOME/.aizen/config.yaml" << 'EOF'
# Aizen Agent Configuration
# Run 'aizen setup' to configure

display:
  tool_progress: true
max_iterations: 90
log_level: INFO
EOF
    echo -e "${G}✓ Default config created${N}"
fi

# Step 9: Run setup wizard
if [ "$RUN_SETUP" = true ]; then
    echo ""
    echo -e "${C}▸ Running setup wizard...${N}"
    echo ""
    "$HOME/.local/bin/aizen" setup || true
fi

# Done!
echo ""
echo -e "${G}${B}╔══════════════════════════════════════════════════════════════╗${N}"
echo -e "${G}${B}║              ✓ Aizen Installed Successfully!                ║${N}"
echo -e "${G}${B}╚══════════════════════════════════════════════════════════════╝${N}"
echo ""
echo "Quick Start:"
echo "  ${C}aizen${N}              Start chatting"
echo "  ${C}aizen setup${N}        Configure provider"
echo ""
echo "Docs: https://github.com/ahmad-ubaidillah/aizen"
echo ""
echo -e "${Y}Run: source ~/.bashrc${N}"
echo ""
