#!/usr/bin/env python
"""
Quick smoke test -- run standalone to verify UE connection and basic commands.

Usage:
    cd Python
    uv run python tests/smoke_test.py
    uv run python tests/smoke_test.py --port 55558

Does NOT need pytest. Prints clear PASS/FAIL for each check.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_client import UnrealTestClient


class SmokeTest:
    def __init__(self, client: UnrealTestClient):
        self.client = client
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def check(self, name: str, fn):
        try:
            fn()
            print(f"  PASS  {name}")
            self.passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name} -- {e}")
            self.failed += 1
        except Exception as e:
            print(f"  FAIL  {name} -- {type(e).__name__}: {e}")
            self.failed += 1

    def summary(self) -> bool:
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*50}")
        print(f"  Total: {total}  |  PASS: {self.passed}  |  FAIL: {self.failed}  |  SKIP: {self.skipped}")
        print(f"{'='*50}")
        return self.failed == 0


def run(client: UnrealTestClient) -> bool:
    import time
    uid = str(int(time.time()))[-6:]
    t = SmokeTest(client)

    # -- 1. Connection --
    print("\n[1] Connection")
    t.check("ping", lambda: client.ok("ping"))

    # -- 2. Engine Info --
    print("\n[2] Engine Info")
    def check_engine_info():
        info = client.ok("get_engine_info")
        assert "engine_version" in info, f"Missing engine_version in {info}"
        print(f"        Engine: {info.get('engine_version')}  Plugin: {info.get('plugin_version')}")
    t.check("get_engine_info", check_engine_info)

    # -- 3. Actor CRUD --
    print("\n[3] Actor Operations")
    actor = f"_SmokeTest_Actor_{uid}"
    t.check("spawn_actor", lambda: client.spawn_actor(actor, "StaticMeshActor", [0, 0, 500]))
    t.check("get_actors_in_level", lambda: client.get_actors())

    def check_find():
        resp = client.ok("find_actors_by_name", {"pattern": "_SmokeTest"})
        assert len(resp.get("actors", [])) > 0, "Spawned actor not found"
    t.check("find_actors_by_name", check_find)

    t.check("set_actor_transform", lambda: client.ok("set_actor_transform", {
        "name": actor, "location": [100, 200, 300], "rotation": [0, 45, 0], "scale": [2, 2, 2],
    }))
    t.check("get_actor_properties", lambda: client.ok("get_actor_properties", {"name": actor}))
    t.check("delete_actor", lambda: client.delete_actor(actor))

    # -- 4. Blueprint --
    print("\n[4] Blueprint Operations")
    bp = f"_SmokeTest_BP_{uid}"
    t.check("create_blueprint", lambda: client.create_blueprint(bp, "Actor"))
    t.check("add_component", lambda: client.add_component(bp, "StaticMeshComponent", "TestMesh"))
    t.check("compile_blueprint", lambda: client.compile_blueprint(bp))

    # -- 5. Blueprint Nodes --
    print("\n[5] Blueprint Nodes")
    t.check("add_event_node", lambda: client.ok("add_blueprint_event_node", {
        "blueprint_name": bp, "event_name": "ReceiveBeginPlay", "node_position": [0, 0],
    }))
    t.check("find_nodes", lambda: client.ok("find_blueprint_nodes", {
        "blueprint_name": bp, "node_type": "Event", "event_name": "ReceiveBeginPlay",
    }))

    # -- 6. Error Handling --
    print("\n[6] Error Handling")
    t.check("unknown_command -> error", lambda: client.fail("nonexistent_command_xyz"))
    t.check("missing_params -> error", lambda: client.fail("spawn_actor", {}))

    # -- Cleanup --
    print("\n[Cleanup]")
    try:
        client.command("delete_actor", {"name": actor})
        print(f"  Deleted test actor: {actor}")
    except Exception:
        pass
    try:
        client.command("delete_asset", {"asset_path": f"/Game/Blueprints/{bp}"})
        print(f"  Deleted test blueprint: {bp}")
    except Exception:
        pass

    return t.summary()


def main():
    parser = argparse.ArgumentParser(description="UnrealMCP Smoke Test")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55557)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()

    client = UnrealTestClient(args.host, args.port, args.timeout)

    print(f"Connecting to Unreal at {args.host}:{args.port} ...")
    if not client.is_connected():
        print(f"\nERROR: Cannot connect to Unreal Engine at {args.host}:{args.port}")
        print("Make sure UE Editor is running with the UnrealMCP plugin enabled.")
        sys.exit(1)

    print("Connected!")
    success = run(client)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
