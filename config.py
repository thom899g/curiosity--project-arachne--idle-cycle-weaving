"""
Configuration for Project Arachne.
"""
import os
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class ResourceLimits:
    """Resource limits for a plugin or the system."""
    cpu_percent: float = 5.0  # Max CPU percent per plugin
    memory_mb: int = 50      # Max memory in MB
    network_mbps: int = 1    # Max network bandwidth in Mbps
    disk_io_ops: int = 100   # Max disk I/O operations per second

@dataclass
class DaemonConfig:
    """Configuration for the Arachne daemon."""
    # Resource monitoring
    idle_cpu_threshold: float = 15.0  # CPU usage below this is considered idle
    idle_memory_threshold: float = 80.0  # Memory usage below this is considered idle
    check_interval: int = 30  # Seconds between checks

    # Plugin paths
    plugin_directory: str = "/var/lib/arachne/plugins"

    # Firebase
    firebase_credential_path: str = "/etc/arachne/firebase_credentials.json"

    # Local cache
    local_cache_path: str = "/var/lib/arachne/local_cache.db"

    # Security
    use_cgroups: bool = True
    use_seccomp: bool = True

    @classmethod
    def from_env(cls) -> 'DaemonConfig':
        """Create configuration from environment variables."""
        return cls(
            idle_cpu_threshold=float(os.getenv('ARACHNE_IDLE_CPU_THRESHOLD', '15.0')),
            idle_memory_threshold=float(os.getenv('ARACHNE_IDLE_MEMORY_THRESHOLD', '80.0')),
            check_interval=int(os.getenv('ARACHNE_CHECK_INTERVAL', '30')),
            plugin_directory=os.getenv('ARACHNE_PLUGIN_DIR', '/var/lib/arachne/plugins'),
            firebase_credential_path=os.getenv('ARACHNE_FIREBASE_CREDENTIALS', '/etc/arachne/firebase_credentials.json'),
            local_cache_path=os.getenv('ARACHNE_LOCAL_CACHE', '/var/lib/arachne/local_cache.db'),
            use_cgroups=os.getenv('ARACHNE_USE_CGROUPS', 'true').lower() == 'true',
            use_seccomp=os.getenv('ARACHNE_USE_SECCOMP', 'true').lower() == 'true',
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

config = DaemonConfig.from_env()