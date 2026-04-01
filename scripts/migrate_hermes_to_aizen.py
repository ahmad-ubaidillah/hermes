     1|#!/usr/bin/env python3
     2|"""
     3|Migration script: Hermes → Aizen
     4|
     5|Migrates user configuration from ~/.hermes to ~/.aizen
     6|Run this once after upgrading from Hermes to Aizen.
     7|
     8|Usage:
     9|    python scripts/migrate_hermes_to_aizen.py [--dry-run]
    10|"""
    11|
    12|import argparse
    13|import json
    14|import os
    15|import re
    16|import shutil
    17|import sys
    18|from pathlib import Path
    19|from typing import Dict, List, Optional, Tuple
    20|
    21|# ANSI colors for terminal output
    22|RED = "\033[91m"
    23|GREEN = "\033[92m"
    24|YELLOW = "\033[93m"
    25|BLUE = "\033[94m"
    26|MAGENTA = "\033[95m"
    27|CYAN = "\033[96m"
    28|RESET = "\033[0m"
    29|BOLD = "\033[1m"
    30|
    31|def print_banner():
    32|    """Print migration banner."""
    33|    print(f"""
    34|{MAGENTA}{BOLD}╔══════════════════════════════════════════════════════════════╗
    35|║  {CYAN}<z> Aizen Migration Tool{MAGENTA}                                    ║
    36|║  {RESET}Hermes → Aizen Configuration Migration{MAGENTA}                   ║
    37|╚══════════════════════════════════════════════════════════════╝{RESET}
    38|""")
    39|
    40|def get_home_dirs() -> Tuple[Path, Path]:
    41|    """Get old and new home directories."""
    42|    old_home = Path.home() / ".hermes"
    43|    new_home = Path.home() / ".aizen"
    44|    return old_home, new_home
    45|
    46|def find_files_to_update(directory: Path) -> List[Path]:
    47|    """Find all files that might need content updates."""
    48|    patterns = ["*.yaml", "*.yml", "*.json", "*.toml", "*.env", "*.txt", "*.md"]
    49|    files = []
    50|    for pattern in patterns:
    51|        files.extend(directory.rglob(pattern))
    52|    return files
    53|
    54|def update_file_content(file_path: Path, dry_run: bool = False) -> int:
    55|    """Update references in a file. Returns count of changes."""
    56|    try:
    57|        content = file_path.read_text()
    58|        original = content
    59|        
    60|        # String replacements
    61|        replacements = [
    62|            (".hermes", ".aizen"),
    63|            ("HERMES_", "AIZEN_"),
    64|            ("hermes-agent", "aizen-agent"),
    65|            ("hermes_cli", "aizen_cli"),
    66|            ("Hermes", "Aizen"),
    67|            ("hermes", "aizen"),
    68|        ]
    69|        
    70|        for old, new in replacements:
    71|            content = content.replace(old, new)
    72|        
    73|        changes = content != original
    74|        if changes and not dry_run:
    75|            file_path.write_text(content)
    76|        
    77|        return 1 if changes else 0
    78|    except Exception as e:
    79|        print(f"  {YELLOW}Warning: Could not update {file_path}: {e}{RESET}")
    80|        return 0
    81|
    82|def migrate_config_yaml(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
    83|    """Migrate config.yaml with content updates."""
    84|    old_config = old_home / "config.yaml"
    85|    new_config = new_home / "config.yaml"
    86|    
    87|    if not old_config.exists():
    88|        return False
    89|    
    90|    if new_config.exists():
    91|        print(f"  {YELLOW}Skipping config.yaml - already exists in ~/.aizen{RESET}")
    92|        return False
    93|    
    94|    if dry_run:
    95|        print(f"  {CYAN}Would migrate: config.yaml{RESET}")
    96|        return True
    97|    
    98|    # Copy and update content
    99|    content = old_config.read_text()
   100|    
   101|    # Update references
   102|    replacements = [
   103|        (".hermes", ".aizen"),
   104|        ("HERMES_", "AIZEN_"),
   105|        ("hermes-agent", "aizen-agent"),
   106|        ("hermes_cli", "aizen_cli"),
   107|    ]
   108|    
   109|    for old, new in replacements:
   110|        content = content.replace(old, new)
   111|    
   112|    new_config.write_text(content)
   113|    print(f"  {GREEN}✓ Migrated: config.yaml{RESET}")
   114|    return True
   115|
   116|def migrate_env_file(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
   117|    """Migrate .env file with environment variable updates."""
   118|    old_env = old_home / ".env"
   119|    new_env = new_home / ".env"
   120|    
   121|    if not old_env.exists():
   122|        return False
   123|    
   124|    if new_env.exists():
   125|        print(f"  {YELLOW}Skipping .env - already exists in ~/.aizen{RESET}")
   126|        return False
   127|    
   128|    if dry_run:
   129|        print(f"  {CYAN}Would migrate: .env{RESET}")
   130|        return True
   131|    
   132|    # Copy and update content
   133|    content = old_env.read_text()
   134|    
   135|    # Update environment variable names
   136|    content = content.replace("HERMES_", "AIZEN_")
   137|    content = content.replace(".hermes", ".aizen")
   138|    
   139|    new_env.write_text(content)
   140|    print(f"  {GREEN}✓ Migrated: .env{RESET}")
   141|    return True
   142|
   143|def migrate_session_db(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
   144|    """Migrate session database."""
   145|    old_db = old_home / "sessions.db"
   146|    new_db = new_home / "sessions.db"
   147|    
   148|    if not old_db.exists():
   149|        return False
   150|    
   151|    if new_db.exists():
   152|        print(f"  {YELLOW}Skipping sessions.db - already exists in ~/.aizen{RESET}")
   153|        return False
   154|    
   155|    if dry_run:
   156|        print(f"  {CYAN}Would migrate: sessions.db{RESET}")
   157|        return True
   158|    
   159|    shutil.copy2(old_db, new_db)
   160|    print(f"  {GREEN}✓ Migrated: sessions.db{RESET}")
   161|    return True
   162|
   163|def migrate_skills_dir(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
   164|    """Migrate skills directory."""
   165|    old_skills = old_home / "skills"
   166|    new_skills = new_home / "skills"
   167|    
   168|    if not old_skills.exists():
   169|        return False
   170|    
   171|    if new_skills.exists():
   172|        print(f"  {YELLOW}Skipping skills/ - already exists in ~/.aizen{RESET}")
   173|        return False
   174|    
   175|    if dry_run:
   176|        print(f"  {CYAN}Would migrate: skills/{RESET}")
   177|        return True
   178|    
   179|    shutil.copytree(old_skills, new_skills)
   180|    print(f"  {GREEN}✓ Migrated: skills/{RESET}")
   181|    return True
   182|
   183|def migrate_skins_dir(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
   184|    """Migrate custom skins directory."""
   185|    old_skins = old_home / "skins"
   186|    new_skins = new_home / "skins"
   187|    
   188|    if not old_skins.exists():
   189|        return False
   190|    
   191|    if new_skins.exists():
   192|        print(f"  {YELLOW}Skipping skins/ - already exists in ~/.aizen{RESET}")
   193|        return False
   194|    
   195|    if dry_run:
   196|        print(f"  {CYAN}Would migrate: skins/{RESET}")
   197|        return True
   198|    
   199|    shutil.copytree(old_skins, new_skins)
   200|    
   201|    # Update skin files
   202|    for skin_file in new_skins.glob("*.yaml"):
   203|        update_file_content(skin_file, dry_run=False)
   204|    
   205|    print(f"  {GREEN}✓ Migrated: skins/{RESET}")
   206|    return True
   207|
   208|def migrate_mcp_config(old_home: Path, new_home: Path, dry_run: bool = False) -> bool:
   209|    """Migrate MCP configuration."""
   210|    old_mcp = old_home / "mcp.json"
   211|    new_mcp = new_home / "mcp.json"
   212|    
   213|    if not old_mcp.exists():
   214|        return False
   215|    
   216|    if new_mcp.exists():
   217|        print(f"  {YELLOW}Skipping mcp.json - already exists in ~/.aizen{RESET}")
   218|        return False
   219|    
   220|    if dry_run:
   221|        print(f"  {CYAN}Would migrate: mcp.json{RESET}")
   222|        return True
   223|    
   224|    # Copy and update content
   225|    content = old_mcp.read_text()
   226|    content = content.replace(".hermes", ".aizen")
   227|    
   228|    new_mcp.write_text(content)
   229|    print(f"  {GREEN}✓ Migrated: mcp.json{RESET}")
   230|    return True
   231|
   232|def check_deprecated_modules(new_home: Path):
   233|    """Check for deprecated module configs and warn the user."""
   234|    warnings = []
   235|    
   236|    # Check for honcho config (deprecated)
   237|    honcho_config = new_home / "config.yaml"
   238|    if honcho_config.exists():
   239|        try:
   240|            content = honcho_config.read_text()
   241|            if "honcho" in content.lower():
   242|                warnings.append(("honcho", 
   243|                    "Honcho module has been removed. Multi-agent orchestration is now built-in.\n"
   244|                    "  Remove 'honcho' from your config.yaml toolsets."))
   245|        except Exception:
   246|            pass
   247|    
   248|    # Check for firecrawl config (deprecated)
   249|    firecrawl_env = new_home / ".env"
   250|    if firecrawl_env.exists():
   251|        try:
   252|            content = firecrawl_env.read_text()
   253|            if "firecrawl" in content.lower():
   254|                warnings.append(("firecrawl",
   255|                    "Firecrawl module has been removed. Use ddgs (DuckDuckGo Search) instead.\n"
   256|                    "  Remove FIRECRAWL_API_KEY from your .env file."))
   257|        except Exception:
   258|            pass
   259|    
   260|    return warnings
   261|
   262|
   263|def run_migration(dry_run: bool = False):
   264|    """Run the complete migration."""
   265|    print_banner()
   266|    
   267|    old_home, new_home = get_home_dirs()
   268|    
   269|    # Check if old config exists
   270|    if not old_home.exists():
   271|        print(f"{YELLOW}No ~/.hermes directory found - nothing to migrate.{RESET}")
   272|        print(f"{CYAN}Aizen will create a fresh configuration on first run.{RESET}")
   273|        return 0
   274|    
   275|    print(f"{BOLD}Source:{RESET}      {old_home}")
   276|    print(f"{BOLD}Destination:{RESET} {new_home}")
   277|    print()
   278|    
   279|    if dry_run:
   280|        print(f"{CYAN}=== DRY RUN - No changes will be made ==={RESET}\n")
   281|    
   282|    # Create new directory if needed
   283|    if not dry_run:
   284|        new_home.mkdir(parents=True, exist_ok=True)
   285|    
   286|    # Run migrations
   287|    print(f"{BOLD}Migrating configuration...{RESET}\n")
   288|    
   289|    migrated = 0
   290|    migrated += 1 if migrate_config_yaml(old_home, new_home, dry_run) else 0
   291|    migrated += 1 if migrate_env_file(old_home, new_home, dry_run) else 0
   292|    migrated += 1 if migrate_session_db(old_home, new_home, dry_run) else 0
   293|    migrated += 1 if migrate_skills_dir(old_home, new_home, dry_run) else 0
   294|    migrated += 1 if migrate_skins_dir(old_home, new_home, dry_run) else 0
   295|    migrated += 1 if migrate_mcp_config(old_home, new_home, dry_run) else 0
   296|    
   297|    # Migrate any other files
   298|    print(f"\n{BOLD}Checking for additional files...{RESET}")
   299|    excluded = {"config.yaml", ".env", "sessions.db", "skills", "skins", "mcp.json"}
   300|    for item in old_home.iterdir():
   301|        if item.name in excluded:
   302|            continue
   303|        if item.name.startswith("."):
   304|            continue
   305|        
   306|        new_path = new_home / item.name
   307|        if new_path.exists():
   308|            print(f"  {YELLOW}Skipping {item.name} - already exists{RESET}")
   309|            continue
   310|        
   311|        if dry_run:
   312|            print(f"  {CYAN}Would migrate: {item.name}{RESET}")
   313|            continue
   314|        
   315|        if item.is_file():
   316|            shutil.copy2(item, new_path)
   317|        else:
   318|            shutil.copytree(item, new_path)
   319|        print(f"  {GREEN}✓ Migrated: {item.name}{RESET}")
   320|        migrated += 1
   321|    
   322|    # Check for deprecated modules
   323|    if not dry_run:
   324|        deprecation_warnings = check_deprecated_modules(new_home)
   325|        if deprecation_warnings:
   326|            print(f"\n{BOLD}{YELLOW}⚠ Deprecated Module Warnings:{RESET}")
   327|            for module, msg in deprecation_warnings:
   328|                print(f"  {BOLD}{module}:{RESET}")
   329|                for line in msg.split('\n'):
   330|                    print(f"    {line}")
   331|    
   332|    # Summary
   333|    print(f"\n{BOLD}{'='*50}{RESET}")
   334|    if dry_run:
   335|        print(f"{CYAN}Dry run complete. Run without --dry-run to apply changes.{RESET}")
   336|    else:
   337|        print(f"{GREEN}✓ Migration complete! Migrated {migrated} item(s).{RESET}")
   338|        print(f"\n{BOLD}Next steps:{RESET}")
   339|        print(f"  1. Run {CYAN}aizen{RESET} to start the agent")
   340|        print(f"  2. Your old config is still at {old_home}")
   341|        print(f"  3. Delete it manually after verifying: {YELLOW}rm -rf ~/.hermes{RESET}")
   342|    
   343|    return 0
   344|
   345|def main():
   346|    """Main entry point."""
   347|    parser = argparse.ArgumentParser(
   348|        description="Migrate Hermes configuration to Aizen",
   349|        formatter_class=argparse.RawDescriptionHelpFormatter,
   350|        epilog="""
   351|Examples:
   352|    python scripts/migrate_hermes_to_aizen.py          # Run migration
   353|    python scripts/migrate_hermes_to_aizen.py --dry-run # Preview changes
   354|"""
   355|    )
   356|    parser.add_argument(
   357|        "--dry-run",
   358|        action="store_true",
   359|        help="Preview changes without making them"
   360|    )
   361|    
   362|    args = parser.parse_args()
   363|    return run_migration(dry_run=args.dry_run)
   364|
   365|if __name__ == "__main__":
   366|    sys.exit(main())
   367|