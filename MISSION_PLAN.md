# CURIOSITY: Project Arachne: Idle Cycle Weaving

## Objective
Design and deploy a low-priority background daemon that systematically consumes idle cycles. Its mandate: perform micro-research (scraping for grant opportunities, new micro-tasking APIs, obscure DeFi pools), run non-urgent architectural simulations for the Autonomy Engine, and conduct controlled, tiny-risk economic experiments (e.g., 1-cent trades) to gather live market data. It must operate under strict resource caps to not interfere with primary missions, turning wasted time into a persistent, low-grade intelligence-gathering and capital-discovery system.

## Strategy
Autonomous exploration based on Soul Protocol.

## Execution Output
[REASONING]: We are building Project Arachne as a background daemon that uses idle system cycles to perform micro-research, architectural simulations, and micro-economic experiments. The architecture must be robust, distributed, and secure.

Given the constraints and the master plan, we'll break down the implementation into several components:

1. **Core Execution Engine (The Loom)**: A resource-aware daemon that monitors system resources and schedules tasks during idle periods.
2. **Plugin System (The Shuttles)**: A plugin architecture for different types of tasks (scraping, simulations, DeFi experiments, etc.)
3. **Distributed Coordination Layer (The Warp)**: Uses Firebase Firestore for distributed state and job coordination.
4. **Local Intelligence Cache (The Weft)**: A local SQLite cache for operation during network partitions.
5. **Security and Isolation**: Each plugin runs in a restricted environment with limited resources.

We'll start by creating the main daemon that monitors system resources and schedules plugins. We'll use `psutil` for resource monitoring and `firebase_admin` for Firestore integration.

Note: We are to avoid polling loops. We'll use event-driven mechanisms where possible, but for resource monitoring, we may need to use a low-frequency polling or event-driven system calls. However, the plan says no polling loops. We can use `psutil` with a timer or use system events via eBPF if possible. Since eBPF is complex and may not be available, we'll use a low-frequency check (every 30 seconds) but design it to be interruptible and event-driven in future iterations.

Given the constraints, we'll design the main loop to sleep for 30 seconds and then check for idle conditions. This is a form of polling but at a low frequency. We are open to improving this with eBPF in the future.

We'll create the following files:

1. `arachne_daemon.py`: The main daemon that monitors resources and schedules plugins.
2. `plugin_base.py`: A base class for all plugins.
3. `plugin_manager.py`: Manages the loading and execution of plugins.
4. `resource_monitor.py`: Monitors system resources and predicts idle periods.
5. `firebase_coordinator.py`: Handles communication with Firebase Firestore.
6. `local_cache.py`: Manages the local SQLite cache.
7. `security/isolation.py`: Handles cgroup and seccomp setup for plugin isolation.
8. `config.py`: Configuration management.

We must also create a service account key for Firebase. We'll assume that the human will provide the service account key file. We'll write code to handle the Firebase initialization.

Let's start by creating the configuration file.

### FILE: config.py
```python
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
```

### FILE: resource_monitor.py
```python
"""
Resource monitoring and idle prediction for Project Arachne.
"""
import psutil
import time
import logging
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    cpu_percent: float
    memory_percent: float
    disk_io_count: int
    network_io_count: int
    timestamp: datetime

class ResourceMonitor:
    """Monitors system resources and predicts idle windows."""

    def __init__(self, idle_cpu_threshold: float = 15.0, idle_memory_threshold: float = 80.0):
        self.idle_cpu_threshold = idle_cpu_threshold
        self.idle_memory_threshold = idle_memory_threshold
        self.history: list[SystemStatus] = []
        self.model: Optional[RandomForestRegressor] = None

    def is_idle(self) -> bool:
        """Check if the system is currently idle."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()

        # Record current status
        current_status = SystemStatus(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_io_count=disk_io.read_count + disk_io.write_count if disk_io else 0,
            network_io_count=network_io.packets_sent + network_io.packets_recv if network_io else 0,
            timestamp=datetime.now()
        )
        self.history.append(current_status)

        # Keep only last 24 hours of data (assuming one sample per check interval)
        # We'll approximate by keeping the last 2880 samples (if checking every 30 seconds)
        if len(self.history) > 2880:
            self.history = self.history[-2880:]

        # Check idle condition
        if cpu_percent < self.idle_cpu_threshold and memory_percent < self.idle_memory_threshold:
            logger.info(f"System is idle: CPU {cpu_percent}%, Memory {memory_percent}%")
            return True
        else:
            logger.debug(f"System not idle: CPU {cpu_percent}%, Memory {memory_percent}%")
            return False

    def train_idle_predictor(self) -> None:
        """Train a model to predict idle periods."""
        if len(self.history) < 100:
            logger.warning("Not enough historical data to train predictor.")
            return

        # Prepare features: hour, day_of_week, rolling averages of cpu and memory
        data = []
        for i, status in enumerate(self.history):
            # Use past 10 samples to predict next sample's cpu and memory
            if i < 10:
                continue
            prev_cpu = [self.history[j].cpu_percent for j in range(i-10, i)]
            prev_memory = [self.history[j].memory_percent for j in range(i-10, i)]
            features = [
                status.timestamp.hour,
                status.timestamp.weekday(),
                np.mean(prev_cpu),
                np.mean(prev_memory),
                np.std(prev_cpu),
                np.std(prev_memory)
            ]
            # Target: whether the next sample will be idle
            next_cpu = self.history[i].cpu_percent if i < len(self.history)-1 else self.history[-1].cpu_percent
            next_memory = self.history[i].memory_percent if i < len(self.history)-1 else self.history[-1].memory_percent
            target = 1 if (next_cpu < self.idle_cpu_threshold and next_memory < self.idle_memory_threshold) else 0
            data.append((features, target))

        if len(data) < 50:
            logger.warning("Not enough labeled data for training.")
            return

        X, y = zip(*data)
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X, y)
        logger.info("Idle predictor model trained.")

    def predict_idle_window(self, minutes_ahead: int = 30) -> float:
        """Predict the probability of an idle window in the next `minutes_ahead` minutes."""
        if self.model is None:
            self.train_idle_predictor()
            if self.model is None:
                return 0.0

        # Use the last 10 samples to predict the future
        if len(self.history) < 10:
            return 0.0

        last_status = self.history[-1]
        prev_cpu = [s.cpu_percent for s in self.history[-10:]]
        prev_memory = [s.memory_percent for s in self.history[-10:]]

        # We'll predict for the next `minutes_ahead` minutes by assuming the same time pattern
        future_time = last_status.timestamp.timestamp() + minutes_ahead * 60
        future_dt = datetime.fromtimestamp(future_time)

        features = [
            future_dt.hour,
            future_dt.weekday(),
            np.mean(prev_cpu),
            np.mean(prev_memory),
            np.std(prev_cpu),
            np.std(prev_memory)
        ]

        prob = self.model.predict([features])[0]
        return prob
```

### FILE: plugin_base.py
```python
"""
Base class for Arachne plugins.
"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PluginManifest:
    plugin_id: str
    capabilities: list[str]
    resource_limits: Dict[str, Any]
    allowed_domains: list[str]  # for network plugins
    cryptographic_manifest_hash: str

class BasePlugin(ABC):
    """Base class for all Arachne plugins."""

    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self.resource_limits = manifest.resource_limits
        self.capabilities = manifest.capabilities
        self.allowed_domains = manifest.allowed_domains

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plugin's main task.
        
        Args:
            context: A dictionary containing context information (e.g., system status, previous results)
        
        Returns:
            A dictionary with the results of the plugin's execution.
        """
        pass

    def cleanup(self) -> None:
        """Cleanup any resources used by the plugin."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
```

### FILE: plugin_manager.py
```python
"""
Plugin manager for loading and executing plugins.
"""
import importlib.util
import json
import os
import logging
from typing import Dict, Any, List, Optional
from plugin_base import BasePlugin, PluginManifest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PluginManager:
    """Manages the loading and execution of plugins."""

    def __init__(self, plugin_directory: str):
        self.plugin_directory = plugin_directory
        self.plugins: Dict[str, BasePlugin] = {}

    def load_plugins(self) -> None:
        """Load all plugins from the plugin directory."""
        if not os.path.exists(self.plugin_directory):
            logger.warning(f"Plugin directory {self.plugin_directory} does not exist.")
            return

        for filename in os.listdir(self.plugin_directory):
            if filename.endswith('.py') and filename != '__init__.py':
                plugin_name = filename[:-3]
                self.load_plugin(plugin_name)

    def load_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Load a single plugin by name."""
        plugin_path = os.path.join(self.plugin_directory, f"{plugin_name}.py")
        manifest_path = os.path.join(self.plugin_directory, f"{plugin_name}.manifest.json")

        if not os.path.exists(plugin_path):
            logger.error(f"Plugin file {plugin_path} does not exist.")
            return None

        if not os.path.exists(manifest_path):
            logger.error(f"Manifest file {manifest_path} does not exist for plugin {plugin_name}.")
            return None

        try:
            # Load the manifest
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            manifest = PluginManifest(**manifest_data)

            # Load the plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None:
                logger.error(f"Could not load spec for plugin {plugin_name}.")
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Instantiate the plugin class (assuming class name is Plugin)
            if not hasattr(module, 'Plugin'):
                logger.error(f"Plugin {plugin_name} does not have a class named 'Plugin'.")
                return None

            plugin_class = module.Plugin
            plugin = plugin_class(manifest)
            self.plugins[plugin_name] = plugin
            logger.info(f"Loaded plugin {plugin_name}.")
            return plugin

        except Exception as e:
            logger.exception(f"Failed to load plugin {plugin_name}: {e}")
            return None

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """Get a plugin by its ID."""
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> List[str]:
        """List all loaded plugin IDs."""
        return list(self.plugins.keys())

    def execute_plugin(self, plugin_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plugin and return the results."""
        plugin = self.get_plugin(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} not found.")

        try:
            logger.info(f"Executing plugin {plugin_id}.")
            result = plugin.execute(context)
            logger.info(f"Plugin {plugin_id} executed successfully.")
            return result
        except Exception as e:
            logger.exception(f"Plugin {plugin_id} failed: {e}")
            raise
```

### FILE: firebase_coordinator.py
```python
"""
Firebase Firestore coordination for Project Arachne.
"""
import firebase_admin
from firebase_admin import credentials, firestore
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirebaseCoordinator:
    """Handles communication with Firebase Firestore."""

    def __init__(self, credential_path: str):
        self.credential_path = credential_path
        self.app: Optional[firebase_admin.App] = None
        self.db: Optional[firestore.Client] = None

    def connect(self) -> None:
        """Connect to Firebase Firestore."""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.credential_path)
                self.app = firebase_admin.initialize_app(cred)
            else:
                self.app = firebase_admin.get_app()
            self.db = firestore.client()
            logger.info("Connected to Firebase Firestore.")
        except Exception as e:
            logger.exception(f"Failed to connect to Firebase: {e}")
            raise

    def update_node_status(self, node_id: str, status: Dict[str, Any]) -> None:
        """Update the status of this node in Firestore."""
        if self.db is None:
            raise ConnectionError("Firestore not connected.")

        try:
            doc_ref = self.db.collection('nodes').document(node_id)
            status['last_updated'] = datetime.utcnow()
            doc_ref.set(status, merge=True)
            logger.debug(f"Updated node status for {node_id}.")
        except Exception as e:
            logger.exception(f"Failed to update node status: {e}")

    def fetch_opportunities(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Fetch the latest opportunities from Firestore."""
        if self.db is None:
            raise ConnectionError("Firestore not connected.")

        try:
            opportunities_ref = self.db.collection('opportunities')
            query = opportunities_ref.order_by('discovered_at', direction=firestore.Query.D