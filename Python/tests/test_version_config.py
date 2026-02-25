"""
Unit tests for version_config.py — does NOT require Unreal Engine running.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from version_config import VersionConfig, SUPPORTED_VERSIONS, DEFAULT_VERSION


class TestVersionConfigLoading:

    def test_default_version(self):
        cfg = VersionConfig()
        assert cfg.version == DEFAULT_VERSION

    def test_explicit_version(self):
        for v in SUPPORTED_VERSIONS:
            cfg = VersionConfig(version=v)
            assert cfg.version == v

    def test_unsupported_version_uses_default_config(self):
        cfg = VersionConfig(version="4.27")
        assert cfg.version == "4.27"
        assert cfg.raw != {}

    def test_set_version(self):
        cfg = VersionConfig(version="5.5")
        assert cfg.set_version("5.4")
        assert cfg.version == "5.4"

    def test_set_unsupported_version_returns_false(self):
        cfg = VersionConfig()
        assert not cfg.set_version("9.9")
        assert cfg.version == DEFAULT_VERSION


class TestVersionConfigValues:

    def test_connection_defaults(self):
        cfg = VersionConfig()
        assert cfg.connection_host == "127.0.0.1"
        assert cfg.connection_port == 55557
        assert cfg.connection_timeout == 5

    def test_dotted_key_get(self):
        cfg = VersionConfig()
        assert cfg.get("connection.host") == "127.0.0.1"
        assert cfg.get("connection.port") == 55557
        assert cfg.get("nonexistent.key", "fallback") == "fallback"

    def test_nested_dotted_key(self):
        cfg = VersionConfig()
        assert cfg.get("api_compatibility.deprecated_commands.create_actor") == "spawn_actor"

    def test_plugin_version(self):
        cfg = VersionConfig()
        assert cfg.plugin_version == "0.1.0"


class TestFeatureFlags:

    def test_ue57_has_all_features(self):
        cfg = VersionConfig(version="5.7")
        assert cfg.has_feature("enhanced_input")
        assert cfg.has_feature("widget_blueprint")
        assert cfg.has_feature("blueprint_editor_library")
        assert cfg.has_feature("blueprint_nodes")

    def test_ue55_has_all_features(self):
        cfg = VersionConfig(version="5.5")
        assert cfg.has_feature("enhanced_input")
        assert cfg.has_feature("widget_blueprint")
        assert cfg.has_feature("blueprint_editor_library")
        assert cfg.has_feature("blueprint_nodes")

    def test_ue53_disables_widget(self):
        cfg = VersionConfig(version="5.3")
        assert not cfg.has_feature("widget_blueprint")
        assert not cfg.has_feature("umg_editor")

    def test_ue54_disables_bp_editor_library(self):
        cfg = VersionConfig(version="5.4")
        assert not cfg.has_feature("blueprint_editor_library")
        assert cfg.has_feature("widget_blueprint")

    def test_nonexistent_feature_returns_false(self):
        cfg = VersionConfig()
        assert not cfg.has_feature("totally_fake_feature")


class TestDeepMerge:

    def test_version_override_merges_correctly(self):
        cfg55 = VersionConfig(version="5.5")
        cfg53 = VersionConfig(version="5.3")
        assert cfg55.has_feature("widget_blueprint")
        assert not cfg53.has_feature("widget_blueprint")
        assert cfg55.connection_port == cfg53.connection_port

    def test_lists_are_replaced_not_appended(self):
        cfg53 = VersionConfig(version="5.3")
        assert "ArrowComponent" not in cfg53.supported_components


class TestSummary:

    def test_summary_is_string(self):
        cfg = VersionConfig()
        s = cfg.summary()
        assert isinstance(s, str)
        assert "Engine Version" in s
        assert cfg.version in s
