"""
Aizen v3.0 Setup Wizard - Simple & Comprehensive

Interactive setup with rich UI covering all v3.0 features.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.aizen_constants import get_aizen_home

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


class SetupWizard:
    """Interactive setup wizard for Aizen v3.0."""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.config_path = get_aizen_home() / "config.json"
        self._load_config()
    
    def _load_config(self):
        """Load existing config."""
        if self.config_path.exists():
            try:
                self.config = json.loads(self.config_path.read_text())
            except:
                self.config = {}
    
    def _save_config(self):
        """Save config to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(self.config, indent=2))
    
    def run(self):
        """Run the complete setup wizard."""
        self._show_welcome()
        
        # Step 1: Model Provider
        self._setup_model_provider()
        
        # Step 2: Terminal Backend
        self._setup_terminal()
        
        # Step 3: v3.0 Features
        self._setup_v3_features()
        
        # Step 4: Messaging Platforms
        self._setup_messaging()
        
        # Step 5: Web Dashboard
        self._setup_dashboard()
        
        # Save and finish
        self._save_config()
        self._show_complete()
    
    def _show_welcome(self):
        """Show welcome message."""
        if RICH_AVAILABLE:
            console.print(Panel.fit(
                "[bold magenta]⚕ Aizen v3.0 Setup Wizard[/bold magenta]\n\n"
                "Configure your Autonomous AI Team\n"
                "Free models via OpenCode included",
                border_style="magenta"
            ))
        else:
            print("\n⚕ Aizen v3.0 Setup Wizard\n")
    
    def _setup_model_provider(self):
        """Setup AI model provider."""
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]▸ Step 1: Model Provider[/bold cyan]\n")
            
            table = Table(show_header=True, header_style="bold")
            table.add_column("#", style="dim")
            table.add_column("Provider")
            table.add_column("Models")
            table.add_column("Cost")
            
            table.add_row("1", "OpenCode", "qwen3.6, mimo, minimax", "FREE")
            table.add_row("2", "OpenAI", "gpt-4, gpt-4o", "Paid")
            table.add_row("3", "Anthropic", "claude-sonnet, claude-opus", "Paid")
            table.add_row("4", "Google", "gemini-pro, gemini-flash", "Paid")
            table.add_row("5", "Custom", "Your API endpoint", "Varies")
            
            console.print(table)
            
            choice = Prompt.ask("\nSelect provider", choices=["1", "2", "3", "4", "5"], default="1")
        else:
            print("\n▸ Step 1: Model Provider\n")
            print("1. OpenCode (FREE - qwen3.6, mimo, minimax)")
            print("2. OpenAI (Paid)")
            print("3. Anthropic (Paid)")
            print("4. Google (Paid)")
            print("5. Custom")
            choice = input("Select [1]: ").strip() or "1"
        
        providers = {
            "1": {"provider": "opencode", "base_url": "", "default": "qwen3.6-plus-free"},
            "2": {"provider": "openai", "base_url": "", "default": "gpt-4o"},
            "3": {"provider": "anthropic", "base_url": "", "default": "claude-sonnet-4.6"},
            "4": {"provider": "google", "base_url": "", "default": "gemini-2.0-flash"},
            "5": {"provider": "custom", "base_url": "", "default": ""},
        }
        
        self.config["model"] = providers.get(choice, providers["1"])
        
        if choice == "5":
            if RICH_AVAILABLE:
                url = Prompt.ask("Enter API base URL")
                model = Prompt.ask("Enter default model name")
            else:
                url = input("API base URL: ").strip()
                model = input("Default model: ").strip()
            self.config["model"]["base_url"] = url
            self.config["model"]["default"] = model
        
        # API key for paid providers
        if choice in ["2", "3", "4"]:
            if RICH_AVAILABLE:
                key = Prompt.ask("Enter API key", password=True)
            else:
                key = input("API key: ").strip()
            self.config["model"]["api_key"] = key
    
    def _setup_terminal(self):
        """Setup terminal backend."""
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]▸ Step 2: Terminal Backend[/bold cyan]\n")
            choice = Prompt.ask(
                "Where should commands run?",
                choices=["1", "2"],
                default="1"
            )
        else:
            print("\n▸ Step 2: Terminal Backend\n")
            print("1. Local (this machine)")
            print("2. SSH Remote")
            choice = input("Select [1]: ").strip() or "1"
        
        if choice == "2":
            if RICH_AVAILABLE:
                host = Prompt.ask("SSH host (e.g., user@host)")
            else:
                host = input("SSH host: ").strip()
            self.config["terminal"] = {"backend": "ssh", "host": host}
        else:
            self.config["terminal"] = {"backend": "local"}
    
    def _setup_v3_features(self):
        """Setup v3.0 features."""
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]▸ Step 3: v3.0 Features[/bold cyan]\n")
            
            features = {
                "intent_gate": Confirm.ask("Enable IntentGate? (smart task routing)", default=True),
                "background_agents": Confirm.ask("Enable Background Agents? (parallel execution)", default=True),
                "lifecycle_hooks": Confirm.ask("Enable Lifecycle Hooks? (fine-grained control)", default=True),
                "hash_edit": Confirm.ask("Enable Hash-Anchored Edit? (zero stale-line editing)", default=True),
                "lsp_integration": Confirm.ask("Enable LSP Integration? (IDE precision)", default=False),
            }
        else:
            print("\n▸ Step 3: v3.0 Features\n")
            features = {
                "intent_gate": input("Enable IntentGate? [Y/n]: ").strip().lower() != "n",
                "background_agents": input("Enable Background Agents? [Y/n]: ").strip().lower() != "n",
                "lifecycle_hooks": input("Enable Lifecycle Hooks? [Y/n]: ").strip().lower() != "n",
                "hash_edit": input("Enable Hash-Anchored Edit? [Y/n]: ").strip().lower() != "n",
                "lsp_integration": input("Enable LSP Integration? [y/N]: ").strip().lower() == "y",
            }
        
        self.config["v3_features"] = features
        
        # Background agent settings
        if features["background_agents"]:
            if RICH_AVAILABLE:
                max_agents = Prompt.ask("Max concurrent agents", default="5")
            else:
                max_agents = input("Max concurrent agents [5]: ").strip() or "5"
            self.config["v3_features"]["max_concurrent_agents"] = int(max_agents)
    
    def _setup_messaging(self):
        """Setup messaging platforms."""
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]▸ Step 4: Messaging Platforms[/bold cyan]\n")
            
            platforms = {}
            
            if Confirm.ask("Setup Telegram? (for daily standups)", default=False):
                token = Prompt.ask("Telegram bot token", password=True)
                chat_id = Prompt.ask("Telegram chat ID")
                platforms["telegram"] = {"token": token, "chat_id": chat_id}
            
            if Confirm.ask("Setup Discord?", default=False):
                token = Prompt.ask("Discord bot token", password=True)
                channel = Prompt.ask("Discord channel ID")
                platforms["discord"] = {"token": token, "channel": channel}
            
            if Confirm.ask("Setup Slack?", default=False):
                token = Prompt.ask("Slack bot token", password=True)
                channel = Prompt.ask("Slack channel")
                platforms["slack"] = {"token": token, "channel": channel}
        else:
            print("\n▸ Step 4: Messaging Platforms\n")
            platforms = {}
            
            if input("Setup Telegram? [y/N]: ").strip().lower() == "y":
                platforms["telegram"] = {
                    "token": input("Bot token: ").strip(),
                    "chat_id": input("Chat ID: ").strip(),
                }
            
            if input("Setup Discord? [y/N]: ").strip().lower() == "y":
                platforms["discord"] = {
                    "token": input("Bot token: ").strip(),
                    "channel": input("Channel ID: ").strip(),
                }
        
        self.config["messaging"] = platforms
        
        # Standup schedule
        if platforms:
            if RICH_AVAILABLE:
                standup_time = Prompt.ask("Daily standup time (HH:MM)", default="09:00")
            else:
                standup_time = input("Daily standup time [09:00]: ").strip() or "09:00"
            self.config["standup_time"] = standup_time
    
    def _setup_dashboard(self):
        """Setup web dashboard."""
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]▸ Step 5: Web Dashboard[/bold cyan]\n")
            
            enable = Confirm.ask("Enable web dashboard?", default=True)
        else:
            print("\n▸ Step 5: Web Dashboard\n")
            enable = input("Enable web dashboard? [Y/n]: ").strip().lower() != "n"
        
        if enable:
            if RICH_AVAILABLE:
                port = Prompt.ask("Dashboard port", default="8000")
                auto_start = Confirm.ask("Auto-start dashboard on boot?", default=False)
            else:
                port = input("Port [8000]: ").strip() or "8000"
                auto_start = input("Auto-start on boot? [y/N]: ").strip().lower() == "y"
            
            self.config["dashboard"] = {
                "enabled": True,
                "port": int(port),
                "auto_start": auto_start,
            }
        else:
            self.config["dashboard"] = {"enabled": False}
    
    def _show_complete(self):
        """Show completion message."""
        if RICH_AVAILABLE:
            console.print("\n")
            console.print(Panel.fit(
                "[bold green]✓ Setup Complete![/bold green]\n\n"
                f"Config saved to: {self.config_path}\n\n"
                "[bold]Next steps:[/bold]\n"
                "  • Run [cyan]aizen[/cyan] to start chatting\n"
                "  • Run [cyan]aizen-dashboard[/cyan] to start web UI\n"
                "  • Run [cyan]aizen setup[/cyan] to reconfigure",
                border_style="green"
            ))
        else:
            print(f"\n✓ Setup Complete!\n")
            print(f"Config saved to: {self.config_path}")
            print("\nNext steps:")
            print("  • Run 'aizen' to start chatting")
            print("  • Run 'aizen-dashboard' to start web UI")


def main():
    """Run the setup wizard."""
    wizard = SetupWizard()
    wizard.run()


if __name__ == "__main__":
    main()
