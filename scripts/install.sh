#!/bin/bash
# ============================================================================
# Aizen Agent - One-Line Installer (Enhanced UI/UX)
# ============================================================================
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash
#
# Options:
#   --skip-setup      Skip setup wizard
#   --no-opencode     Skip OpenCode check
#   --minimal         Minimal install
#   --branch NAME     Install specific branch
#
# ============================================================================

set -e

# Enhanced Colors & Styles
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
BOLD='\033[1m'
DIM='\033[2m'
ITALIC='\033[3m'
UNDERLINE='\033[4m'
NC='\033[0m' # No Color

# Progress tracking
STEPS_TOTAL=9
CURRENT_STEP=0

# Spinner animation
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while kill -0 $pid 2>/dev/null; do
        local temp=${spinstr#?}
        printf " \r${CYAN}%s${NC}" "$temp"
        spinstr=$temp${temp%"$temp"}
        sleep $delay
    done
    printf " \r"
}

# Step counter
step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    local msg="$1"
    printf "${CYAN}[${CURRENT_STEP}/${STEPS_TOTAL}]${NC} ${msg}"
}

# Success/fail indicators
success() { printf "${GREEN}✓${NC} %s\n" "$1"; }
fail() { printf "${RED}✗${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
info() { printf "${DIM}→${NC} %s\n" "$1"; }

# Progress bar
progress_bar() {
    local current=$1
    local total=$2
    local width=30
    local percent=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))
    printf "${CYAN}["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "${NC}] ${percent}%%"
}

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

# Clear screen for fresh start
clear

# ============================================================================
# BANNER
# ============================================================================
cat << 'BANNER'
${CYAN}
     ██████╗ ███████╗████████╗██████╗  ██████╗ ██████╗  ██████╗  █████╗ ██████╗ ██████╗ 
    ██╔════╝ ██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██╔══██╗██╔══██╗██╔══██╗
    ██║  ███╗█████╗    ██║   ██████╔╝██║   ██║██████╔╝██║   ██║███████║██║  ██║██████╔╝
    ██║   ██║██╔══╝    ██║   ██╔══██╗██║   ██║██╔══██╗██║   ██║██╔══██║██║  ██║██╔══██╗
    ╚██████╔╝███████╗   ██║   ██║  ██║╚██████╔╝██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
     ╚═════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 
${NC}
BANNER

echo ""
echo -e "${WHITE}${BOLD}                   ⚕  Autonomous AI Team Platform  ⚕${NC}"
echo ""
echo -e "${DIM}              Build software with minimal human intervention${NC}"
echo ""

# ============================================================================
# OS CHECK
# ============================================================================
OS="$(uname -s)"
if [[ "$OS" != "Linux" && "$OS" != "Darwin" ]]; then
    echo ""
    fail "Unsupported operating system: $OS"
    echo ""
    echo "Aizen currently supports:"
    echo "  • Linux (Ubuntu 20.04+, Debian 11+)"
    echo "  • macOS (12.0+)"
    echo ""
    exit 1
fi

success "Detected $OS system"

# Config
INSTALL_DIR="$HOME/.aizen/aizen-agent"
AIZEN_HOME="$HOME/.aizen"

echo ""
echo -e "${WHITE}${BOLD}Installation Progress:${NC}"
echo ""

# Step 1: Install uv
step "Installing uv (fast Python package manager)... "
if ! command -v uv &>/dev/null; then
    # Show download progress
    if curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; then
        export PATH="$HOME/.local/bin:$PATH"
        success "uv installed"
    else
        fail "Failed to install uv"
        echo "Please install uv manually: https://astral.sh/uv"
        exit 1
    fi
else
    success "uv already installed"
fi

# Step 2: Clone/Update repository
step "Installing Aizen Agent... "
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR"
    if git fetch origin "$BRANCH" 2>/dev/null && git checkout "$BRANCH" 2>/dev/null; then
        git pull origin "$BRANCH" >/dev/null 2>&1 || true
        success "Updated to $BRANCH branch"
    else
        success "Using existing installation"
    fi
else
    mkdir -p "$(dirname "$INSTALL_DIR")"
    if git clone -b "$BRANCH" https://github.com/ahmad-ubaidillah/hermes.git "$INSTALL_DIR" 2>/dev/null; then
        cd "$INSTALL_DIR"
        success "Cloned from repository"
    else
        fail "Failed to clone repository"
        exit 1
    fi
fi

# Step 3: Setup Python environment
step "Setting up Python environment... "
rm -rf "$INSTALL_DIR/venv" "$INSTALL_DIR/.venv" 2>/dev/null || true
if uv venv venv --python 3.11 >/dev/null 2>&1; then
    source venv/bin/activate
    success "Python 3.11 virtual environment created"
else
    fail "Failed to create virtual environment"
    exit 1
fi

# Step 4: Install packages
step "Installing Python packages... "
if uv pip install -e ".[all]" >/dev/null 2>&1; then
    success "All packages installed"
else
    warn "Some optional packages failed, continuing anyway..."
    if uv pip install -e "." >/dev/null 2>&1; then
        success "Core packages installed"
    else
        fail "Failed to install packages"
        exit 1
    fi
fi

# Step 5: Check & Install OpenCode
if [ "$CHECK_OPENCODE" = true ]; then
    step "Checking OpenCode... "
    if ! command -v opencode &>/dev/null; then
        info "OpenCode not found, installing..."
        if command -v npm &>/dev/null; then
            if npm install -g @opencode-ai/opencode >/dev/null 2>&1; then
                success "OpenCode installed"
            else
                warn "OpenCode install failed (optional)"
            fi
        else
            warn "npm not found, skipping OpenCode"
        fi
    else
        success "OpenCode found"
    fi
fi

# Step 6: Create config directory
step "Creating configuration directory... "
mkdir -p "$AIZEN_HOME"
success "Config directory ready"

# Step 7: Create aizen command
step "Creating aizen command... "
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/aizen" << 'CMD' || { fail "Failed to create command"; exit 1; }
#!/bin/bash
# Aizen CLI - Auto-detects credentials from OpenCode if available

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
success "Command created"

# Step 8: Add to PATH
step "Adding to PATH... "
PATH_ADDED=false
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$rc" ] && ! grep -q '\.local/bin' "$rc" 2>/dev/null; then
        echo "" >> "$rc"
        echo "# Aizen Agent" >> "$rc"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        echo 'export PAGER=cat' >> "$rc"  # Fix help to display without vim-style pager
        PATH_ADDED=true
    fi
done
export PATH="$HOME/.local/bin:$PATH"
if [ "$PATH_ADDED" = true ]; then
    success "Added to PATH (restart shell or run: source ~/.bashrc)"
else
    success "Already in PATH"
fi

# Step 9: Create default config
step "Creating default configuration... "
if [ ! -f "$AIZEN_HOME/config.yaml" ]; then
    cat > "$AIZEN_HOME/config.yaml" << 'EOF'
# Aizen Agent Configuration
# Run 'aizen setup' to configure

display:
  tool_progress: true
  skin: default

max_iterations: 90
log_level: INFO
EOF
    success "Default config created"
else
    success "Using existing config"
fi

# Step 10: Run setup wizard (optional)
if [ "$RUN_SETUP" = true ]; then
    echo ""
    read -p "$(echo -e ${CYAN}'Run setup wizard now? [Y/n]: '${NC})" -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        echo ""
        "$HOME/.local/bin/aizen" setup || true
    fi
fi

# ============================================================================
# DONE
# ============================================================================
echo ""
echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║                    ✓ Installation Complete!                         ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Activating Aizen in current shell...${NC}"
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    [ -f "$rc" ] && source "$rc" 2>/dev/null
done
export PATH="$HOME/.local/bin:$PATH"
export PAGER=cat

if command -v aizen &>/dev/null; then
    echo -e "${GREEN}✓ Aizen is ready!${NC}"
else
    echo -e "${YELLOW}⚠ Please restart your terminal to use aizen${NC}"
fi

echo ""
echo -e "${WHITE}${BOLD}Quick Start:${NC}"
echo ""
echo -e "  ${CYAN}aizen${NC}              Start Aizen CLI"
echo -e "  ${CYAN}aizen setup${NC}        Configure provider & settings"
echo -e "  ${CYAN}aizen --help${NC}       Show all commands"
echo ""
echo -e "${DIM}Tips:${NC}"
echo -e "  • Use ${CYAN}aizen --model opencode/qwen3.6-plus-free${NC} for free models"
echo -e "  • Check docs at ${CYAN}https://github.com/ahmad-ubaidillah/hermes${NC}"
echo ""
echo -e "${YELLOW}⚕  Execute with Zen ⚕${NC}"
echo ""
