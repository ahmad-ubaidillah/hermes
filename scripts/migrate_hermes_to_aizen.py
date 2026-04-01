#!/usr/bin/env python3
"""
Migration script: Hermes → Aizen

Migrates user configuration from ~/.hermes to ~/.aizen
Run this once after upgrading from Hermes to Aizen.

Usage:
    python scripts/migrate_hermes_to_aizen.py [--dry-run]
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ANSI colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_banner():
    """Print migration banner."""
    print(f"""
{MAGENTA}{BOLD}╔══════════════════════════════════════════════════════════════╗
║  {CYAN}<z> Aizen Migration Tool{MAGENTA}                                    ║
║  {RESET}Hermes → Aizen Configuration Migration{MAGENTA}                   ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")

def get_home_dirs() -> Tuple[Path, Path]:
    """Get old and new home directories."""
    old_home = Path.home() / ".hermes"
    new_home = Path.home() / ".aizen"
    return old_home, new_home

def find_files_to_update(directory: Path) -> List[Path]:
    """Find all files that might need content updates."""
    patterns = ["*.yaml", "*.yml", "*.json", "*.toml", "*.env", "*.txt", "*.md"]
    files = []
    for pattern in patterns:
        files.extend(directory.rglob(pattern))
    return files

def update_file_content(file_path: Path, dry_run: bool = False) -> int:
    """Update references in a file. Returns count of changes."""
    try:
        content = file_path.read_text()
        original = content
        
        # String replacements
        replacements = [
            (".hermes", ".aizen"),
            ("HERMES_", "AIZEN_"),
            ("hermes-agent", "aizen-agent"),
            ("hermes_cli", "aizen_cli"),
            ("Hermes", "Aizen"),
            ("hermes", "aizen"),
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        changes = content != original
        if changes and not dry_run:
            file_path.write_text(content)
        
        return 1 if changes else 0
    except Exception as e:
        print(f"  {YELLOW}Warning: Could not update {file_path}: {e}{RESET}")
        return 0

def migrate_config_yaml(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
    """Migrate config.yaml with content updates."""
    old_config = old_home / "config.yaml"
    new_config = new_home / "config.yaml"
    
    if not old_config.exists():
        return False
    
    if new_config.exists():
        print(f"  {YELLOW}Skipping config.yaml - already exists in ~/.aizen{RESET}")
        return False
    
    if dry_run:
        print(f"  {CYAN}Would migrate: config.yaml{RESET}")
        return True
    
    # Copy and update content
    content = old_config.read_text()
    
    # Update references
    replacements = [
        (".hermes", ".aizen"),
        ("HERMES_", "AIZEN_"),
        ("hermes-agent", "aizen-agent"),
        ("hermes_cli", "aizen_cli"),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    new_config.write_text(content)
    print(f"  {GREEN}✓ Migrated: config.yaml{RESET}")
    return True

def migrate_env_file(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
    """Migrate .env file with environment variable updates."""
    old_env = old_home / ".env"
    new_env = new_home / ".env"
    
    if not old_env.exists():
        return False
    
    if new_env.exists():
        print(f"  {YELLOW}Skipping .env - already exists in ~/.aizen{RESET}")
        return False
    
    if dry_run:
        print(f"  {CYAN}Would migrate: .env{RESET}")
        return True
    
    # Copy and update content
    content = old_env.read_text()
    
    # Update environment variable names
    content = content.replace("HERMES_", "AIZEN_")
    content = content.replace(".hermes", ".aizen")
    
    new_env.write_text(content)
    print(f"  {GREEN}✓ Migrated: .env{RESET}")
    return True

def migrate_session_db(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
    """Migrate session database."""
    old_db = old_home / "sessions.db"
    new_db = new_home / "sessions.db"
    
    if not old_db.exists():
        return False
    
    if new_db.exists():
        print(f"  {YELLOW}Skipping sessions.db - already exists in ~/.aizen{RESET}")
        return False
    
    if dry_run:
        print(f"  {CYAN}Would migrate: sessions.db{RESET}")
        return True
    
    shutil.copy2(old_db, new_db)
    print(f"  {GREEN}✓ Migrated: sessions.db{RESET}")
    return True

def migrate_skills_dir(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
    """Migrate skills directory."""
    old_skills = old_home / "skills"
    new_skills = new_home / "skills"
    
    if not old_skills.exists():
        return False
    
    if new_skills.exists():
        print(f"  {YELLOW}Skipping skills/ - already exists in ~/.aizen{RESET}")
        return False
    
    if dry_run:
        print(f"  {CYAN}Would migrate: skills/{RESET}")
        return True
    
    shutil.copytree(old_skills, new_skills)
    print(f"  {GREEN}✓ Migrated: skills/{RESET}")
    return True

def migrate_skins_dir(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
    """Migrate custom skins directory."""
    old_skins = old_home / "skins"
    new_skins = new_home / "skins"
    
    if not old_skins.exists():
        return False
    
    if new_skins.exists():
        print(f"  {YELLOW}Skipping skins/ - already exists in ~/.aizen{RESET}")
        return False
    
    if dry_run:
        print(f"  {CYAN}Would migrate: skins/{RESET}")
        return True
    
    shutil.copytree(old_skins, new_skins)
    
    # Update skin files
    for skin_file in new_skins.glob("*.yaml"):
        update_file_content(skin_file, dry_run=False)
    
    print(f"  {GREEN}✓ Migrated: skins/{RESET}")
    return True

def migrate_mcp_config(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
    """Migrate MCP configuration."""
    old_mcp = old_home / "mcp.json"
    new_mcp = new_home / "mcp.json"
    
    if not old_mcp.exists():
        return False
    
    if new_mcp.exists():
        print(f"  {YELLOW}Skipping mcp.json - already exists in ~/.aizen{RESET}")
        return False
    
    if dry_run:
        print(f"  {CYAN}Would migrate: mcp.json{RESET}")
        return True
    
    # Copy and update content
    content = old_mcp.read_text()
    content = content.replace(".hermes", ".aizen")
    
    new_mcp.write_text(content)
    print(f"  {GREEN}✓ Migrated: mcp.json{RESET}")
    return True

def run_migration(dry_run: bool = False):
    """Run the complete migration."""
    print_banner()
    
    old_home, new_home = get_home_dirs()
    
    # Check if old config exists
    if not old_home.exists():
        print(f"{YELLOW}No ~/.hermes directory found - nothing to migrate.{RESET}")
        print(f"{CYAN}Aizen will create a fresh configuration on first run.{RESET}")
        return 0
    
    print(f"{BOLD}Source:{RESET}      {old_home}")
    print(f"{BOLD}Destination:{RESET} {new_home}")
    print()
    
    if dry_run:
        print(f"{CYAN}=== DRY RUN - No changes will be made ==={RESET}\n")
    
    # Create new directory if needed
    if not dry_run:
        new_home.mkdir(parents=True, exist_ok=True)
    
    # Run migrations
    print(f"{BOLD}Migrating configuration...{RESET}\n")
    
    migrated = 0
    migrated += 1 if migrate_config_yaml(old_home, new_home, dry_run) else 0
    migrated += 1 if migrate_env_file(old_home, new_home, dry_run) else 0
    migrated += 1 if migrate_session_db(old_home, new_home, dry_run) else 0
    migrated += 1 if migrate_skills_dir(old_home, new_home, dry_run) else 0
    migrated += 1 if migrate_skins_dir(old_home, new_home, dry_run) else 0
    migrated += 1 if migrate_mcp_config(old_home, new_home, dry_run) else 0
    
    # Migrate any other files
    print(f"\n{BOLD}Checking for additional files...{RESET}")
    excluded = {"config.yaml", ".env", "sessions.db", "skills", "skins", "mcp.json"}
    for item in old_home.iterdir():
        if item.name in excluded:
            continue
        if item.name.startswith("."):
            continue
        
        new_path = new_home / item.name
        if new_path.exists():
            print(f"  {YELLOW}Skipping {item.name} - already exists{RESET}")
            continue
        
        if dry_run:
            print(f"  {CYAN}Would migrate: {item.name}{RESET}")
            continue
        
        if item.is_file():
            shutil.copy2(item, new_path)
        else:
            shutil.copytree(item, new_path)
        print(f"  {GREEN}✓ Migrated: {item.name}{RESET}")
        migrated += 1
    
    # Summary
    print(f"\n{BOLD}{'='*50}{RESET}")
    if dry_run:
        print(f"{CYAN}Dry run complete. Run without --dry-run to apply changes.{RESET}")
    else:
        print(f"{GREEN}✓ Migration complete! Migrated {migrated} item(s).{RESET}")
        print(f"\n{BOLD}Next steps:{RESET}")
        print(f"  1. Run {CYAN}aizen{RESET} to start the agent")
        print(f"  2. Your old config is still at {old_home}")
        print(f"  3. Delete it manually after verifying: {YELLOW}rm -rf ~/.hermes{RESET}")
    
    return 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate Hermes configuration to Aizen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/migrate_hermes_to_aizen.py          # Run migration
    python scripts/migrate_hermes_to_aizen.py --dry-run # Preview changes
"""
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them"
    )
    
    args = parser.parse_args()
    return run_migration(dry_run=args.dry_run)

if __name__ == "__main__":
    sys.exit(main())
