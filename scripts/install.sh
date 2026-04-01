#!/bin/bash
# ============================================================================
# Aizen v3.0 Installer - Simple & Comprehensive
# ============================================================================
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/aizen/main/scripts/install.sh | bash
#
# Options:
#   --skip-setup      Skip setup wizard
#   --no-opencode     Skip OpenCode installation
#   --minimal         Minimal install (no OpenCode, no dashboard)
#   --branch NAME     Install specific branch
#
# ============================================================================

set -e

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[0;33m'; B='\033[0;34m'; M='\033[0;35m'; C='\033[0;36m'
N='\033[0m'; BOLD='\033[1m'

# Config
REPO="https://github.com/ahmad-ubaidillah/aizen.git"
HOME_HERMES="$HOME/.aizen"
INSTALL_DIR="${AIZEN_INSTALL_DIR:-$HOME_HERMES/aizen-agent}"
PYTHON_VER="3.11"
BRANCH="main"
RUN_SETUP=true
INSTALL_OPENCODE=true
MINIMAL=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup) RUN_SETUP=false; shift ;;
        --no-opencode) INSTALL_OPENCODE=false; shift ;;
        --minimal) MINIMAL=true; INSTALL_OPENCODE=false; shift ;;
        --branch) BRANCH="$2"; shift 2 ;;
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        -h|--help)
            echo "Aizen v3.0 Installer"
            echo "Usage: install.sh [OPTIONS]"
            echo "  --skip-setup    Skip setup wizard"
            echo "  --no-opencode   Skip OpenCode (free models)"
            echo "  --minimal       Minimal install"
            echo "  --branch NAME   Branch to install"
            echo "  --dir PATH      Install directory"
            exit 0 ;;
        *) shift ;;
    esac
done

# Banner
echo -e "${M}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ⚕ Aizen v3.0 Installer                         ║"
echo "║         Autonomous AI Team - Free + Powerful                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${N}"

# OS check
OS="$(uname -s)"
[[ "$OS" != "Linux" && "$OS" != "Darwin" ]] && { echo -e "${R}Unsupported OS${N}"; exit 1; }

# Step 1: Dependencies
echo -e "${B}▸ Installing dependencies...${N}"
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq 2>/dev/null || true
    sudo apt-get install -y -qq git curl python3 python3-pip python3-venv nodejs npm 2>/dev/null || true
elif command -v brew &>/dev/null; then
    brew install git curl python@3.11 node npm 2>/dev/null || true
fi
echo -e "${G}✓ Dependencies${N}"

# Step 2: uv (fast Python installer)
echo -e "${B}▸ Installing uv (fast Python installer)...${N}"
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    export PATH="$HOME/.local/bin:$PATH"
fi
echo -e "${G}✓ uv installed${N}"

# Step 3: Clone Aizen
echo -e "${B}▸ Cloning Aizen v3.0...${N}"
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR" && git pull origin "$BRANCH" >/dev/null 2>&1 || true
else
    git clone -b "$BRANCH" "$REPO" "$INSTALL_DIR" >/dev/null 2>&1
    cd "$INSTALL_DIR"
fi
echo -e "${G}✓ Repository ready${N}"

# Step 4: Python environment
echo -e "${B}▸ Creating Python environment...${N}"
uv venv venv --python "$PYTHON_VER" >/dev/null 2>&1
source venv/bin/activate
uv pip install -e ".[all]" >/dev/null 2>&1
echo -e "${G}✓ Python packages${N}"

# Step 5: OpenCode (free models)
if [ "$INSTALL_OPENCODE" = true ] && [ "$MINIMAL" = false ]; then
    echo -e "${B}▸ Installing OpenCode (free AI models)...${N}"
    if command -v npm &>/dev/null; then
        npm install -g @opencode-ai/opencode >/dev/null 2>&1 || true
        echo -e "${G}✓ OpenCode installed${N}"
        echo ""
        echo -e "${C}  Free models available:${N}"
        echo "    • opencode/qwen3.6-plus-free"
        echo "    • opencode/mimo-v2-omni-free"
        echo "    • opencode/minimax-m2.5-free"
        echo "    • opencode/nemotron-3-super-free"
    fi
fi

# Step 6: Create aizen command
echo -e "${B}▸ Creating aizen command...${N}"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/aizen" << 'CMD'
#!/bin/bash
source "$HOME/.aizen/aizen-agent/venv/bin/activate"
python "$HOME/.aizen/aizen-agent/cli.py" "$@"
CMD
chmod +x "$HOME/.local/bin/aizen"

# Create dashboard command
cat > "$HOME/.local/bin/aizen-dashboard" << 'CMD'
#!/bin/bash
source "$HOME/.aizen/aizen-agent/venv/bin/activate"
python -m web.backend.main "$@"
CMD
chmod +x "$HOME/.local/bin/aizen-dashboard"
echo -e "${G}✓ Commands created${N}"

# Step 7: Config directory
mkdir -p "$HOME_HERMES"

# Step 8: Setup wizard
if [ "$RUN_SETUP" = true ]; then
    echo ""
    echo -e "${B}▸ Running setup wizard...${N}"
    python cli.py setup || true
fi

# Done
echo ""
echo -e "${G}${BOLD}╔══════════════════════════════════════════════════════════════╗${N}"
echo -e "${G}${BOLD}║              ✓ Aizen v3.0 Installed!                        ║${N}"
echo -e "${G}${BOLD}╚══════════════════════════════════════════════════════════════╝${N}"
echo ""
echo -e "${BOLD}Quick Start:${N}"
echo ""
echo "  ${C}aizen${N}              Start chatting"
echo "  ${C}aizen-dashboard${N}    Start web dashboard"
echo "  ${C}opencode run \"task\"${N} Free AI coding"
echo ""
echo -e "${BOLD}Documentation:${N} https://github.com/ahmad-ubaidillah/aizen"
echo ""
