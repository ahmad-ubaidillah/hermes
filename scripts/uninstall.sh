#!/bin/bash
# ============================================================================
# Aizen Agent - Uninstaller
# ============================================================================
#
# Usage:
#   aizen uninstall              # Interactive mode
#   aizen uninstall --keep-data   # Keep configs/sessions
#   aizen uninstall --full        # Remove everything
#   aizen uninstall --force       # No confirmation
#
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m'

# Parse args
KEEP_DATA=true
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-data) KEEP_DATA=true; shift ;;
        --full) KEEP_DATA=false; shift ;;
        --force) FORCE=true; shift ;;
        -h|--help)
            echo "Aizen Uninstaller"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --keep-data   Keep configs and sessions (default)"
            echo "  --full        Remove everything including all data"
            echo "  --force       Skip confirmation"
            echo "  -h, --help    Show this help"
            exit 0
            ;;
        *) shift ;;
    esac
done

AIZEN_HOME="$HOME/.aizen"
INSTALL_DIR="$HOME/.aizen/aizen-agent"

# Banner
echo ""
echo -e "${RED}${BOLD}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}${BOLD}║                    ⚕ Aizen Agent Uninstaller                      ║${NC}"
echo -e "${RED}${BOLD}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Show what's affected
echo -e "${CYAN}${BOLD}Current Installation:${NC}"
echo "  Code:    $INSTALL_DIR"
echo "  Config: $AIZEN_HOME/config.yaml"
echo "  Data:   $AIZEN_HOME/sessions/, $AIZEN_HOME/logs/"
echo ""

# Confirmation
if [ "$FORCE" = false ]; then
    echo -e "${YELLOW}${BOLD}This will remove Aizen from your system.${NC}"
    if [ "$KEEP_DATA" = true ]; then
        echo -e "${GREEN}Keeping configuration and data.${NC}"
    else
        echo -e "${RED}WARNING: Removing EVERYTHING including all data!${NC}"
    fi
    echo ""
    read -p "Type 'yes' to confirm: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Cancelled."
        exit 0
    fi
fi

echo ""
echo -e "${CYAN}Uninstalling...${NC}"
echo ""

# 1. Stop gateway service if running
echo -e "${CYAN}[1/5]${NC} Checking for services..."
if command -v systemctl &>/dev/null; then
    systemctl --user stop aizen-gateway 2>/dev/null || true
    systemctl --user disable aizen-gateway 2>/dev/null || true
fi

# 2. Remove PATH entries
echo -e "${CYAN}[2/5]${NC} Removing PATH entries..."
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$rc" ]; then
        # Remove Aizen-related PATH entries
        sed -i '/# Aizen Agent/d' "$rc" 2>/dev/null || true
        sed -i '/aizen-agent/d' "$rc" 2>/dev/null || true
        sed -i '/\.local\/bin/d' "$rc" 2>/dev/null || true
        sed -i '/PAGER=cat/d' "$rc" 2>/dev/null || true
    fi
done

# 3. Remove wrapper script
echo -e "${CYAN}[3/5]${NC} Removing aizen command..."
rm -f "$HOME/.local/bin/aizen" 2>/dev/null || true

# 4. Remove installation directory
echo -e "${CYAN}[4/5]${NC} Removing installation directory..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓ Removed $INSTALL_DIR${NC}"
else
    echo -e "${YELLOW}⚠ Installation directory not found${NC}"
fi

# 5. Remove Aizen home data
echo -e "${CYAN}[5/5]${NC} Cleaning up..."
if [ "$KEEP_DATA" = false ]; then
    if [ -d "$AIZEN_HOME" ]; then
        rm -rf "$AIZEN_HOME"
        echo -e "${GREEN}✓ Removed all data${NC}"
    fi
else
    echo -e "${GREEN}✓ Configuration preserved in $AIZEN_HOME${NC}"
fi

# Done
echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║                    ✓ Uninstall Complete!                            ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$KEEP_DATA" = true ]; then
    echo -e "${CYAN}Your configuration has been preserved.${NC}"
    echo "To reinstall later with your settings intact:"
    echo -e "  ${CYAN}curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash${NC}"
    echo ""
fi

echo -e "${YELLOW}Please restart your terminal or run:${NC}"
echo -e "  ${CYAN}source ~/.bashrc${NC} (or ~/.zshrc)"
echo ""
