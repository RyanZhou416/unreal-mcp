"""
Shared pytest fixtures for Unreal MCP tests.

Fixtures automatically detect whether a UE Editor is running and skip
integration tests if not. All test names include unique suffixes to
prevent collisions, and all created objects are cleaned up after tests.
"""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.test_client import UnrealTestClient

_session_uid = str(int(time.time()))[-6:]


BP_ASSET_BASE = "/Game/Blueprints/"


def _cleanup_test_actors(client: UnrealTestClient):
    """Delete all actors whose names start with _Test_ or _SmokeTest_ to clean up previous runs."""
    try:
        for pattern in ("_Test_", "_SmokeTest_"):
            resp = client.command("find_actors_by_name", {"pattern": pattern})
            if resp.get("status") == "success":
                actors = resp.get("result", {}).get("actors", [])
                for actor in actors:
                    name = actor.get("name", "") if isinstance(actor, dict) else str(actor)
                    try:
                        client.command("delete_actor", {"name": name})
                    except Exception:
                        pass
    except Exception:
        pass


@pytest.fixture(scope="session")
def ue_client() -> UnrealTestClient:
    """Session-scoped client. Skips the entire session if UE is unreachable."""
    client = UnrealTestClient()
    if not client.is_connected():
        pytest.skip("Unreal Engine not running — skipping integration tests")
    _cleanup_test_actors(client)
    return client


@pytest.fixture(scope="session")
def session_uid() -> str:
    """Unique suffix for this test session to avoid name collisions."""
    return _session_uid


@pytest.fixture
def client() -> UnrealTestClient:
    """Per-test client (no connection check — use for unit tests too)."""
    return UnrealTestClient()


@pytest.fixture
def uid(request, session_uid) -> str:
    """Short unique id for each test: combines session uid + test index."""
    return f"{session_uid}_{abs(hash(request.node.name)) % 10000}"


@pytest.fixture
def actor_cleanup(ue_client):
    """Fixture that tracks created actors and deletes them after the test."""
    created = []

    class Tracker:
        def spawn(self, name: str, actor_type: str = "StaticMeshActor", location=None):
            result = ue_client.spawn_actor(name, actor_type, location)
            created.append(name)
            return result

    yield Tracker()

    for name in reversed(created):
        try:
            ue_client.command("delete_actor", {"name": name})
        except Exception:
            pass


@pytest.fixture
def bp_cleanup(ue_client):
    """Fixture that tracks created blueprints and deletes them after the test."""
    created = []

    class Tracker:
        def create(self, name: str, parent_class: str = "Actor"):
            result = ue_client.create_blueprint(name, parent_class)
            created.append(name)
            return result

    yield Tracker()

    for name in reversed(created):
        try:
            ue_client.command("delete_asset", {"asset_path": f"{BP_ASSET_BASE}{name}"})
        except Exception:
            pass
