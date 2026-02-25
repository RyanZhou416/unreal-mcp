"""
Shared TCP test client for Unreal MCP.

Provides a reusable UnrealTestClient that any test script or pytest test can
import to talk directly to the UnrealMCP C++ plugin over TCP.
"""

import json
import socket
import logging
from typing import Dict, Any, List

logger = logging.getLogger("UnrealMCP.TestClient")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55557
DEFAULT_TIMEOUT = 10


class UnrealTestClient:
    """Lightweight TCP client that sends JSON commands to the UnrealMCP plugin.

    Usage::

        client = UnrealTestClient()
        result = client.command("get_actors_in_level")
        print(result)

    Each ``command()`` call opens a fresh TCP connection (matching the current
    plugin behaviour that closes the socket after every response).
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def command(self, cmd_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a single command and return the parsed JSON response.

        Raises ``ConnectionError`` if the plugin is unreachable and
        ``RuntimeError`` on protocol-level errors.
        """
        payload = {"type": cmd_type, "params": params or {}}
        raw = json.dumps(payload)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
            sock.sendall(raw.encode("utf-8"))
            data = self._recv_full(sock)
            response = json.loads(data.decode("utf-8"))
            return response
        except socket.timeout:
            raise ConnectionError(f"Timeout connecting to Unreal at {self.host}:{self.port}")
        except ConnectionRefusedError:
            raise ConnectionError(
                f"Connection refused — is UE Editor running with UnrealMCP plugin on {self.host}:{self.port}?"
            )
        finally:
            sock.close()

    def _recv_full(self, sock: socket.socket) -> bytes:
        """Receive until we have a complete JSON object."""
        chunks: List[bytes] = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            data = b"".join(chunks)
            try:
                json.loads(data.decode("utf-8"))
                return data
            except json.JSONDecodeError:
                continue
        if chunks:
            return b"".join(chunks)
        raise RuntimeError("Connection closed before receiving data")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        """Return True if the plugin TCP server is reachable."""
        try:
            result = self.command("ping")
            return result.get("status") == "success"
        except (ConnectionError, RuntimeError):
            return False

    def ok(self, cmd_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command and assert that it succeeds. Returns the *result* dict."""
        resp = self.command(cmd_type, params)
        assert resp.get("status") == "success", f"Command '{cmd_type}' failed: {resp.get('error', resp)}"
        return resp.get("result", {})

    def fail(self, cmd_type: str, params: Dict[str, Any] = None) -> str:
        """Send a command and assert that it fails. Returns the error message."""
        resp = self.command(cmd_type, params)
        assert resp.get("status") == "error", f"Expected '{cmd_type}' to fail but got: {resp}"
        return resp.get("error", "")

    # ------------------------------------------------------------------
    # Actor helpers
    # ------------------------------------------------------------------

    def spawn_actor(self, name: str, actor_type: str = "StaticMeshActor",
                    location: List[float] = None) -> Dict[str, Any]:
        return self.ok("spawn_actor", {
            "name": name,
            "type": actor_type,
            "location": location or [0, 0, 0],
            "rotation": [0, 0, 0],
        })

    def delete_actor(self, name: str) -> Dict[str, Any]:
        return self.ok("delete_actor", {"name": name})

    def get_actors(self) -> List[Dict]:
        result = self.ok("get_actors_in_level")
        return result.get("actors", [])

    # ------------------------------------------------------------------
    # Blueprint helpers
    # ------------------------------------------------------------------

    def create_blueprint(self, name: str, parent_class: str = "Actor") -> Dict[str, Any]:
        resp = self.command("create_blueprint", {"name": name, "parent_class": parent_class})
        if resp.get("status") == "success":
            return resp.get("result", {})
        if "already exists" in resp.get("error", "").lower():
            return {"name": name, "already_existed": True}
        assert False, f"create_blueprint failed: {resp.get('error', resp)}"

    def compile_blueprint(self, name: str) -> Dict[str, Any]:
        return self.ok("compile_blueprint", {"blueprint_name": name})

    def add_component(self, bp_name: str, comp_type: str, comp_name: str) -> Dict[str, Any]:
        return self.ok("add_component_to_blueprint", {
            "blueprint_name": bp_name,
            "component_type": comp_type,
            "component_name": comp_name,
        })

    # ------------------------------------------------------------------
    # Asset helpers
    # ------------------------------------------------------------------

    def delete_asset(self, asset_path: str) -> Dict[str, Any]:
        return self.ok("delete_asset", {"asset_path": asset_path})

    # ------------------------------------------------------------------
    # Engine info
    # ------------------------------------------------------------------

    def engine_info(self) -> Dict[str, Any]:
        return self.ok("get_engine_info")
