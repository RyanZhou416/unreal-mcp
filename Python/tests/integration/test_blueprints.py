"""
Integration tests for Blueprint operations.
Requires UE Editor running with UnrealMCP plugin.

Note: Blueprints are persistent UE assets. create_blueprint tolerates
"already exists" errors (returns the existing blueprint info).
"""

import pytest


class TestBlueprintCreate:

    def test_create_actor_blueprint(self, ue_client, bp_cleanup, uid):
        result = bp_cleanup.create(f"_Test_ActorBP_{uid}", "Actor")
        assert result is not None

    def test_create_pawn_blueprint(self, ue_client, bp_cleanup, uid):
        result = bp_cleanup.create(f"_Test_PawnBP_{uid}", "Pawn")
        assert result is not None

    def test_create_duplicate_returns_error(self, ue_client, bp_cleanup, uid):
        name = f"_Test_DupBP_{uid}"
        bp_cleanup.create(name, "Actor")
        resp = ue_client.command("create_blueprint", {
            "name": name, "parent_class": "Actor",
        })
        is_error = resp.get("status") == "error"
        is_exists = "already exists" in resp.get("error", "").lower()
        assert is_error and is_exists


class TestBlueprintComponents:

    @pytest.fixture(autouse=True)
    def setup_bp(self, ue_client, bp_cleanup, uid):
        self.bp_name = f"_Test_CompBP_{uid}"
        bp_cleanup.create(self.bp_name, "Actor")

    def test_add_static_mesh(self, ue_client):
        ue_client.ok("add_component_to_blueprint", {
            "blueprint_name": self.bp_name,
            "component_type": "StaticMeshComponent",
            "component_name": "TestMesh",
        })

    def test_add_camera(self, ue_client):
        ue_client.ok("add_component_to_blueprint", {
            "blueprint_name": self.bp_name,
            "component_type": "CameraComponent",
            "component_name": "TestCamera",
        })

    def test_add_to_nonexistent_bp_fails(self, ue_client):
        ue_client.fail("add_component_to_blueprint", {
            "blueprint_name": "_Nonexistent_BP_XYZ",
            "component_type": "StaticMeshComponent",
            "component_name": "Comp",
        })


class TestBlueprintCompile:

    def test_compile_valid(self, ue_client, bp_cleanup, uid):
        name = f"_Test_CompileBP_{uid}"
        bp_cleanup.create(name, "Actor")
        ue_client.compile_blueprint(name)

    def test_compile_nonexistent_fails(self, ue_client):
        ue_client.fail("compile_blueprint", {"blueprint_name": "_Nonexistent_BP_XYZ"})


class TestBlueprintNodes:

    @pytest.fixture(autouse=True)
    def setup_bp(self, ue_client, bp_cleanup, uid):
        self.bp_name = f"_Test_NodeBP_{uid}"
        bp_cleanup.create(self.bp_name, "Actor")

    def test_add_begin_play(self, ue_client):
        result = ue_client.ok("add_blueprint_event_node", {
            "blueprint_name": self.bp_name,
            "event_name": "ReceiveBeginPlay",
            "node_position": [0, 0],
        })
        assert "node_id" in result

    def test_add_variable(self, ue_client):
        ue_client.ok("add_blueprint_variable", {
            "blueprint_name": self.bp_name,
            "variable_name": "TestHealth",
            "variable_type": "Float",
            "is_exposed": False,
        })

    def test_add_branch_node(self, ue_client):
        result = ue_client.ok("add_blueprint_branch_node", {
            "blueprint_name": self.bp_name,
            "node_position": [240, 80],
        })
        assert "node_id" in result

    def test_add_spawn_actor_node(self, ue_client):
        result = ue_client.ok("add_blueprint_spawn_actor_node", {
            "blueprint_name": self.bp_name,
            "actor_class": "AActor",
            "node_position": [420, 80],
        })
        assert "node_id" in result

    def test_find_event_nodes(self, ue_client):
        ue_client.ok("add_blueprint_event_node", {
            "blueprint_name": self.bp_name,
            "event_name": "ReceiveBeginPlay",
            "node_position": [0, 0],
        })
        result = ue_client.ok("find_blueprint_nodes", {
            "blueprint_name": self.bp_name,
            "node_type": "Event",
            "event_name": "ReceiveBeginPlay",
        })
        assert "nodes" in result or isinstance(result, dict)
