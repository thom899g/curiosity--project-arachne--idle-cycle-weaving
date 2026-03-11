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