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