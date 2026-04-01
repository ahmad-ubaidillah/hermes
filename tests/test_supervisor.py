"""Tests for Hermes Supervisor Module."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestProcessSupervisor:
    """Test ProcessSupervisor class."""
    
    def test_supervisor_creation(self):
        """Test ProcessSupervisor can be created."""
        from supervisor import ProcessSupervisor
        
        sup = ProcessSupervisor(command=["echo", "test"])
        
        assert sup.command == ["echo", "test"]
        assert sup.max_restarts == 5
        assert sup.running is False
    
    def test_supervisor_custom_config(self):
        """Test ProcessSupervisor with custom config."""
        from supervisor import ProcessSupervisor
        
        sup = ProcessSupervisor(
            command=["python", "-c", "print(1)"],
            max_restarts=10,
            restart_delay=2.0,
        )
        
        assert sup.max_restarts == 10
        assert sup.restart_delay == 2.0


class TestRestartLogic:
    """Test restart logic."""
    
    def test_should_restart_initial(self):
        """Test should_restart returns True initially."""
        from supervisor import ProcessSupervisor
        
        sup = ProcessSupervisor(command=["echo", "test"])
        assert sup._should_restart() is True
    
    def test_restart_delay_backoff(self):
        """Test restart delay exponential backoff."""
        from supervisor import ProcessSupervisor
        
        sup = ProcessSupervisor(
            command=["echo", "test"],
            restart_delay=1.0,
            max_delay=60.0,
        )
        
        delay1 = sup._get_restart_delay()
        sup.restart_count = 1
        delay2 = sup._get_restart_delay()
        
        assert delay2 > delay1


class TestSystemdService:
    """Test systemd service generation."""
    
    def test_generate_systemd_service(self):
        """Test systemd service file generation."""
        from supervisor import generate_systemd_service
        
        content = generate_systemd_service(
            name="hermes",
            user="hermes",
            working_dir="/opt/hermes",
            command="python -m gateway.run",
        )
        
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content


class TestSupervisorIntegration:
    """Integration tests for supervisor."""
    
    def test_import_works(self):
        """Test module can be imported."""
        import supervisor
        assert supervisor is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
