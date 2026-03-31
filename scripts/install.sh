#!/bin/bash
# ============================================================================
# Hermes v3.0 Installer
# ============================================================================
# Installation script for Linux and macOS.
# Installs Hermes + OpenCode for free AI models.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash
#
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration
REPO_URL="https://github.com/ahmad-ubaidillah/hermes.git"
HERMES_HOME="$HOME/.hermes"
INSTALL_DIR="${HERMES_INSTALL_DIR:-$HERMES_HOME/hermes-agent}"
PYTHON_VERSION="3.11"

# Options
RUN_SETUP=true
INSTALL_OPENCODE=true
BRANCH="main"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup)
            RUN_SETUP=false
            shift
            ;;
        --no-opencode)
            INSTALL_OPENCODE=false
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Hermes v3.0 Installer"
            echo ""
            echo "Usage: install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-setup    Skip interactive setup wizard"
            echo "  --no-opencode   Skip OpenCode installation"
            echo "  --branch NAME   Git branch to install (default: main)"
            echo "  --dir PATH      Installation directory"
            echo "  -h, --help      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# Helper functions
# ============================================================================

print_banner() {
    echo ""
    echo -e "${MAGENTA}${BOLD}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│             ⚕ Hermes v3.0 Installer                     │"
    echo "├─────────────────────────────────────────────────────────┤"
    echo "│  Autonomous AI Team Platform                            │"
    echo "│  Free models via OpenCode                               │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}!${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Main installation
# ============================================================================

print_banner

# Check OS
OS="$(uname -s)"
case "$OS" in
    Linux*)  ;;
    Darwin*) ;;
    *)       log_error "Unsupported OS: $OS"; exit 1 ;;
esac

# Install dependencies
log_info "Installing dependencies..."

if check_command "apt-get" && [ "$OS" = "Linux" ]; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq git curl python3 python3-pip python3-venv nodejs npm > /dev/null 2>&1 || true
elif check_command "brew" && [ "$OS" = "Darwin" ]; then
    brew install git curl python@3.11 node npm > /dev/null 2>&1 || true
fi

log_success "Dependencies installed"

# Install uv (fast Python installer)
if ! check_command "uv"; then
    log_info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1
    export PATH="$HOME/.local/bin:$PATH"
    log_success "uv installed"
else
    log_success "uv already installed"
fi

# Clone repository
log_info "Cloning Hermes v3.0..."
if [ -d "$INSTALL_DIR" ]; then
    log_warn "Directory exists, updating..."
    cd "$INSTALL_DIR"
    git pull origin "$BRANCH" > /dev/null 2>&1 || true
else
    git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR" > /dev/null 2>&1
    cd "$INSTALL_DIR"
fi
log_success "Repository ready"

# Create virtual environment
log_info "Creating Python virtual environment..."
uv venv venv --python "$PYTHON_VERSION" > /dev/null 2>&1
source venv/bin/activate
log_success "Virtual environment created"

# Install Python dependencies
log_info "Installing Python packages..."
uv pip install -e ".[all]" > /dev/null 2>&1
log_success "Python packages installed"

# Install OpenCode for free models
if [ "$INSTALL_OPENCODE" = true ]; then
    log_info "Installing OpenCode for free AI models..."
    
    if check_command "npm"; then
        npm install -g @opencode-ai/opencode > /dev/null 2>&1 || true
        log_success "OpenCode installed"
        
        # Show available models
        echo ""
        log_info "Available free models:"
        opencode models 2>/dev/null | sed 's/^/    /' || true
    else
        log_warn "npm not found, skipping OpenCode"
    fi
fi

# Create hermes command symlink
log_info "Creating hermes command..."
HERMES_BIN="$HOME/.local/bin/hermes"
mkdir -p "$HOME/.local/bin"
cat > "$HERMES_BIN" << 'HERMES_SCRIPT'
#!/bin/bash
source "$HOME/.hermes/hermes-agent/venv/bin/activate"
python "$HOME/.hermes/hermes-agent/cli.py" "$@"
HERMES_SCRIPT
chmod +x "$HERMES_BIN"
log_success "hermes command created"

# Create config directory
mkdir -p "$HERMES_HOME"

# Run setup wizard
if [ "$RUN_SETUP" = true ]; then
    log_info "Running setup wizard..."
    python cli.py setup || true
fi

# ============================================================================
# Done
# ============================================================================

echo ""
echo -e "${GREEN}${BOLD}✓ Hermes v3.0 installed successfully!${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Reload your shell:"
echo "     source ~/.bashrc  # or ~/.zshrc"
echo ""
echo "  2. Start Hermes:"
echo "     hermes"
echo ""
echo "  3. Use OpenCode for free AI coding:"
echo "     opencode run \"implement feature X\""
echo ""
echo "  4. Start Web Dashboard:"
echo "     python -m web.backend.main"
echo ""
echo "Documentation: https://github.com/ahmad-ubaidillah/hermes"
echo ""
