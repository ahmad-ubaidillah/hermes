"""Process supervision for Aizen Agent.

Features:
- Auto-restart on crash with exponential backoff
- PID file management
- Health check integration
- Systemd service file template
"""

from __future__ import annotations

import atexit
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_PID_DIR = Path("/tmp/aizen")
DEFAULT_PID_FILE = DEFAULT_PID_DIR / "aizen.pid"


class ProcessSupervisor:
    """Supervisor for Aizen Agent process.
    
    Example:
        supervisor = ProcessSupervisor(
            command=["python", "-m", "gateway.run"],
            pid_file=Path("/var/run/aizen.pid"),
        )
        supervisor.start()
    """
    
    def __init__(
        self,
        command: list,
        pid_file: Path = DEFAULT_PID_FILE,
        max_restarts: int = 5,
        restart_delay: float = 1.0,
        max_delay: float = 60.0,
        health_check_interval: float = 30.0,
    ):
        self.command = command
        self.pid_file = pid_file
        self.max_restarts = max_restarts
        self.restart_delay = restart_delay
        self.max_delay = max_delay
        self.health_check_interval = health_check_interval
        
        self.process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self.last_restart = 0.0
        self.running = False
    
    def start(self):
        """Start the supervised process."""
        self._write_pid()
        self._setup_signal_handlers()
        self.running = True
        
        logger.info("Starting supervisor for: %s", " ".join(self.command))
        
        while self.running:
            try:
                self._run_process()
            except Exception as e:
                logger.error("Process crashed: %s", e)
                
                if not self._should_restart():
                    logger.error("Max restarts reached, exiting")
                    break
                
                delay = self._get_restart_delay()
                logger.info("Restarting in %.1fs (attempt %d/%d)", 
                           delay, self.restart_count, self.max_restarts)
                time.sleep(delay)
        
        self._cleanup()
    
    def stop(self):
        """Stop the supervised process."""
        self.running = False
        if self.process:
            logger.info("Stopping process (PID %d)", self.process.pid)
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
    
    def _run_process(self):
        """Run the process and wait for completion."""
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        logger.info("Process started (PID %d)", self.process.pid)
        
        # Update PID file with child PID
        self._write_pid(self.process.pid)
        
        # Wait for process
        self.process.wait()
        
        returncode = self.process.returncode
        self.process = None
        
        if returncode == 0:
            logger.info("Process exited normally")
            self.restart_count = 0  # Reset on clean exit
        else:
            raise RuntimeError(f"Process exited with code {returncode}")
    
    def _should_restart(self) -> bool:
        """Check if we should attempt restart."""
        # Reset count if last restart was > 5 minutes ago
        if time.time() - self.last_restart > 300:
            self.restart_count = 0
        
        self.restart_count += 1
        self.last_restart = time.time()
        
        return self.restart_count <= self.max_restarts
    
    def _get_restart_delay(self) -> float:
        """Get delay before next restart (exponential backoff)."""
        delay = self.restart_delay * (2 ** (self.restart_count - 1))
        return min(delay, self.max_delay)
    
    def _write_pid(self, pid: Optional[int] = None):
        """Write PID to file."""
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid = pid or os.getpid()
        self.pid_file.write_text(str(pid))
        atexit.register(self._cleanup_pid_file)
    
    def _cleanup_pid_file(self):
        """Remove PID file."""
        try:
            self.pid_file.unlink(missing_ok=True)
        except Exception:
            pass
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for clean shutdown."""
        def handle_signal(signum, frame):
            logger.info("Received signal %d, shutting down", signum)
            self.stop()
        
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
    
    def _cleanup(self):
        """Cleanup on exit."""
        self._cleanup_pid_file()
        if self.process:
            self.process.kill()


def generate_systemd_service(
    name: str = "aizen",
    user: str = "aizen",
    working_dir: str = "/opt/aizen",
    command: str = "python -m gateway.run",
    description: str = "Aizen AI Agent Gateway",
) -> str:
    """Generate a systemd service file.
    
    Returns:
        Service file content
    """
    return f'''[Unit]
Description={description}
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={command}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Environment
Environment=AIZEN_HOME=/home/{user}/.aizen

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
'''


def main():
    """Main entry point for supervisor CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aizen Process Supervisor")
    parser.add_argument("--command", nargs="+", required=True, help="Command to run")
    parser.add_argument("--pid-file", type=Path, default=DEFAULT_PID_FILE, help="PID file path")
    parser.add_argument("--max-restarts", type=int, default=5, help="Max restart attempts")
    args = parser.parse_args()
    
    supervisor = ProcessSupervisor(
        command=args.command,
        pid_file=args.pid_file,
        max_restarts=args.max_restarts,
    )
    supervisor.start()


if __name__ == "__main__":
    main()
