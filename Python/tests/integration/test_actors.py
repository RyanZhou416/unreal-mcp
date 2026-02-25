"""
Integration tests for Actor operations.
Requires UE Editor running with UnrealMCP plugin.
"""

import pytest


class TestActorSpawn:

    def test_spawn_static_mesh(self, ue_client, actor_cleanup, uid):
        name = f"_Test_Cube_{uid}"
        result = actor_cleanup.spawn(name, "StaticMeshActor", [0, 0, 200])
        assert "name" in result or "actor" in str(result).lower()

    def test_spawn_point_light(self, ue_client, actor_cleanup, uid):
        actor_cleanup.spawn(f"_Test_Light_{uid}", "PointLight", [100, 0, 200])

    def test_spawn_camera(self, ue_client, actor_cleanup, uid):
        actor_cleanup.spawn(f"_Test_Camera_{uid}", "CameraActor", [0, 0, 300])

    def test_spawn_duplicate_name_fails(self, ue_client, actor_cleanup, uid):
        name = f"_Test_Dup_{uid}"
        actor_cleanup.spawn(name, "StaticMeshActor")
        error = ue_client.fail("spawn_actor", {
            "name": name, "type": "StaticMeshActor",
            "location": [0, 0, 0], "rotation": [0, 0, 0],
        })
        assert "already exists" in error.lower() or "exist" in error.lower()

    def test_spawn_unknown_type_fails(self, ue_client):
        error = ue_client.fail("spawn_actor", {
            "name": "_Test_BadType_XYZ", "type": "FakeActorType",
            "location": [0, 0, 0], "rotation": [0, 0, 0],
        })
        assert len(error) > 0


class TestActorQuery:

    def test_get_actors_returns_list(self, ue_client):
        actors = ue_client.get_actors()
        assert isinstance(actors, list)

    def test_find_by_name(self, ue_client, actor_cleanup, uid):
        name = f"_Test_Findable_{uid}"
        actor_cleanup.spawn(name, "StaticMeshActor")
        result = ue_client.ok("find_actors_by_name", {"pattern": name})
        assert len(result.get("actors", [])) >= 1


class TestActorTransform:

    def test_set_location(self, ue_client, actor_cleanup, uid):
        name = f"_Test_Move_{uid}"
        actor_cleanup.spawn(name, "StaticMeshActor")
        ue_client.ok("set_actor_transform", {
            "name": name, "location": [999, 888, 777],
        })

    def test_set_full_transform(self, ue_client, actor_cleanup, uid):
        name = f"_Test_TRS_{uid}"
        actor_cleanup.spawn(name, "StaticMeshActor")
        ue_client.ok("set_actor_transform", {
            "name": name,
            "location": [100, 200, 300],
            "rotation": [0, 45, 0],
            "scale": [2, 2, 2],
        })

    def test_set_transform_nonexistent_fails(self, ue_client):
        ue_client.fail("set_actor_transform", {
            "name": "_Nonexistent_Actor_XYZ",
            "location": [0, 0, 0],
        })


class TestActorDelete:

    def test_delete_existing(self, ue_client, uid):
        name = f"_Test_DelMe_{uid}"
        ue_client.spawn_actor(name, "StaticMeshActor")
        ue_client.delete_actor(name)

    def test_delete_nonexistent_fails(self, ue_client):
        ue_client.fail("delete_actor", {"name": "_Nonexistent_XYZ"})
