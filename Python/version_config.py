"""
Version Configuration System for Unreal MCP.

Manages version-specific configurations for different Unreal Engine versions.
Supports auto-detection from the engine and manual override via environment variables.
"""

import json
import os
import logging
from typing import Dict, List

logger = logging.getLogger("UnrealMCP")

SUPPORTED_VERSIONS = ["5.3", "5.4", "5.5", "5.7"]
DEFAULT_VERSION = "5.7"


class VersionConfig:
    """Loads and manages version-specific configuration for Unreal Engine MCP.

    Configuration is resolved by deep-merging a version-specific override file
    on top of default.json.  The target version can come from:
      1. An explicit *version* argument
      2. The UE_VERSION environment variable
      3. Auto-detection via the ``get_engine_info`` TCP command
      4. DEFAULT_VERSION ("5.5") as the final fallback
    """

    def __init__(self, version: str = ""):
        self._config: Dict = {}
        self._version = version or os.environ.get("UE_VERSION", DEFAULT_VERSION)
        self._detected = False
        self._load_config()

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_config(self):
        """Load default config and merge the version-specific override."""
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")

        default_path = os.path.join(config_dir, "default.json")
        if not os.path.exists(default_path):
            logger.error(f"Default config not found: {default_path}")
            self._config = {}
            return

        with open(default_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

        version_file = f"ue{self._version}.json"
        version_path = os.path.join(config_dir, version_file)
        if os.path.exists(version_path):
            with open(version_path, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            self._deep_merge(self._config, overrides)
            logger.info(f"Loaded version config: {version_file}")
        else:
            logger.warning(f"No version config found for UE {self._version}, using defaults")

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """Recursively merge *override* into *base* in place."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                VersionConfig._deep_merge(base[key], value)
            else:
                base[key] = value

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    @property
    def version(self) -> str:
        return self._version

    @property
    def detected(self) -> bool:
        """Whether the version was auto-detected from the engine."""
        return self._detected

    def set_version(self, version: str) -> bool:
        """Switch to a different UE version and reload the config.

        Returns True on success, False if the version is unsupported.
        """
        if version not in SUPPORTED_VERSIONS:
            logger.warning(f"Unsupported UE version: {version}. Supported: {SUPPORTED_VERSIONS}")
            return False
        self._version = version
        self._load_config()
        logger.info(f"Version config switched to UE {version}")
        return True

    def auto_detect_version(self, connection) -> bool:
        """Query the engine for its version via ``get_engine_info`` and switch config.

        *connection* must expose a ``send_command(cmd, params)`` method that
        returns a dict (the standard ``UnrealConnection``).
        """
        try:
            result = connection.send_command("get_engine_info", {})
            if not result or result.get("status") != "success":
                logger.warning("Could not auto-detect UE version (command failed)")
                return False

            engine_info = result.get("result", {})
            full_version = engine_info.get("engine_version", "")
            parts = full_version.split(".")
            if len(parts) >= 2:
                short_version = f"{parts[0]}.{parts[1]}"
                if short_version in SUPPORTED_VERSIONS:
                    self.set_version(short_version)
                    self._detected = True
                    logger.info(f"Auto-detected UE version: {short_version} (full: {full_version})")
                    return True
                else:
                    logger.warning(
                        f"Detected UE version {short_version} is not in supported list "
                        f"{SUPPORTED_VERSIONS}. Using default {DEFAULT_VERSION}"
                    )
        except Exception as e:
            logger.warning(f"Auto-detection failed: {e}")
        return False

    # ------------------------------------------------------------------
    # Config accessors
    # ------------------------------------------------------------------

    @property
    def raw(self) -> Dict:
        """Return the full merged configuration dict."""
        return self._config

    def get(self, dotted_key: str, default=None):
        """Look up a value using a dot-separated key path.

        Example::

            config.get("connection.port")       # -> 55557
            config.get("features.umg_editor")    # -> True / False
        """
        keys = dotted_key.split(".")
        node = self._config
        for k in keys:
            if isinstance(node, dict):
                node = node.get(k)
                if node is None:
                    return default
            else:
                return default
        return node

    def has_feature(self, feature_name: str) -> bool:
        """Check whether a feature flag is enabled for the current version."""
        return bool(self._config.get("features", {}).get(feature_name, False))

    # --- Shortcut properties ---

    @property
    def connection_host(self) -> str:
        return self.get("connection.host", "127.0.0.1")

    @property
    def connection_port(self) -> int:
        return self.get("connection.port", 55557)

    @property
    def connection_timeout(self) -> int:
        return self.get("connection.timeout", 5)

    @property
    def supported_actor_types(self) -> List[str]:
        return self._config.get("supported_actor_types", [])

    @property
    def supported_components(self) -> List[str]:
        return self._config.get("supported_components", [])

    @property
    def supported_parent_classes(self) -> List[str]:
        return self._config.get("supported_parent_classes", [])

    @property
    def blueprint_events(self) -> List[str]:
        return self._config.get("blueprint_events", [])

    @property
    def umg_widget_types(self) -> List[str]:
        return self._config.get("umg_widget_types", [])

    @property
    def deprecated_commands(self) -> Dict[str, str]:
        return self.get("api_compatibility.deprecated_commands", {})

    @property
    def plugin_version(self) -> str:
        return self._config.get("plugin_version", "0.1.0")

    @property
    def log_level(self) -> str:
        return self.get("logging.level", "DEBUG")

    @property
    def log_file(self) -> str:
        return self.get("logging.file", "unreal_mcp.log")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Return a human-readable summary of the active configuration."""
        features = self._config.get("features", {})
        enabled = [k for k, v in features.items() if v]
        disabled = [k for k, v in features.items() if not v]
        lines = [
            f"Unreal MCP Version Config",
            f"  Engine Version : UE {self._version}",
            f"  Plugin Version : {self.plugin_version}",
            f"  Detected       : {self._detected}",
            f"  Connection     : {self.connection_host}:{self.connection_port}",
            f"  Enabled Features  : {', '.join(enabled)}",
            f"  Disabled Features : {', '.join(disabled)}",
            f"  Actor Types       : {', '.join(self.supported_actor_types)}",
            f"  Components        : {', '.join(self.supported_components)}",
        ]
        return "\n".join(lines)


# Singleton instance — initialised lazily on first access
_global_config: VersionConfig = None


def get_config() -> VersionConfig:
    """Return the global VersionConfig singleton, creating it if necessary."""
    global _global_config
    if _global_config is None:
        _global_config = VersionConfig()
        logger.info(f"Initialised version config for UE {_global_config.version}")
    return _global_config


def init_config(version: str = "") -> VersionConfig:
    """(Re)initialise the global VersionConfig with a specific version."""
    global _global_config
    _global_config = VersionConfig(version)
    logger.info(f"Version config initialised: UE {_global_config.version}")
    return _global_config
