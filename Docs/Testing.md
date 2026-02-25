# 测试指南

## 概览

项目采用三层测试策略，覆盖从纯 Python 逻辑到完整 UE 集成的全部场景：

| 层级 | 名称 | 需要 UE | 运行时间 | 用途 |
|------|------|---------|----------|------|
| 1 | 单元测试 | 否 | < 1 秒 | 验证 Python 逻辑（配置、解析等） |
| 2 | 冒烟测试 | 是 | ~10 秒 | 快速确认核心链路通畅 |
| 3 | 集成测试 | 是 | ~30 秒 | 完整验证各命令的正确性和边界情况 |

**设计原则：** UE 未运行时，所有需要连接的测试自动 SKIP，不会报错。

---

## 前置准备

```bash
cd Python
uv venv --python 3.11    # Python 3.14 暂不支持 pydantic-core，用 3.11
uv pip install -e ".[dev]"
```

dev 依赖包含：
- `pytest >= 8.0` — 测试框架
- `pytest-timeout >= 2.3` — 防止测试挂起（默认 30 秒超时）
- `pytest-cov >= 5.0` — 覆盖率统计
- `ruff >= 0.8` — 代码检查与格式化

---

## 第 1 层：单元测试

不需要 UE 运行，可随时执行。

```bash
cd Python
uv run pytest tests/test_version_config.py -v
```

### 覆盖范围

| 测试类 | 说明 |
|--------|------|
| `TestVersionConfigLoading` | 配置文件加载、版本切换、不支持版本的回退 |
| `TestVersionConfigValues` | 连接参数、点号路径访问、嵌套键获取 |
| `TestFeatureFlags` | 各 UE 版本的功能开关（5.3/5.4/5.5 差异） |
| `TestDeepMerge` | 版本覆盖的深度合并、列表替换（非追加） |
| `TestSummary` | 摘要输出格式 |

### 扩展方式

在 `tests/` 目录下新增 `test_*.py` 文件即可被 pytest 自动发现。适合测试不依赖 UE 的逻辑：

```python
# tests/test_my_parser.py
def test_parse_location():
    from tools.editor_tools import parse_location
    assert parse_location([1, 2, 3]) == (1.0, 2.0, 3.0)
```

---

## 第 2 层：冒烟测试

独立脚本，不依赖 pytest，输出人类友好的 PASS/FAIL。

### 前置条件

1. 启动 UE 编辑器，加载 `MCPGameProject`
2. 确认 UnrealMCP 插件已启用（自动在 `127.0.0.1:55557` 监听）

### 运行

```bash
cd Python
uv run python tests/smoke_test.py
```

可指定参数：

```bash
uv run python tests/smoke_test.py --host 127.0.0.1 --port 55558 --timeout 15
```

### 检查项

| 分组 | 检查内容 |
|------|----------|
| Connection | `ping` 连通性 |
| Engine Info | `get_engine_info` 返回引擎版本和插件版本 |
| Actor Operations | `spawn_actor`、`get_actors_in_level`、`find_actors_by_name`、`set_actor_transform`、`get_actor_properties`、`delete_actor` |
| Blueprint | `create_blueprint`、`add_component`、`compile_blueprint` |
| Blueprint Nodes | `add_event_node (BeginPlay)`、`find_blueprint_nodes` |
| Error Handling | 未知命令返回 error、缺少参数返回 error |

### 输出示例

```
Connecting to Unreal at 127.0.0.1:55557 ...
Connected!

[1] Connection
  PASS  ping

[2] Engine Info
  PASS  get_engine_info
        Engine: 5.5.0  Plugin: 1.0

[3] Actor Operations
  PASS  spawn_actor
  PASS  get_actors_in_level
  PASS  find_actors_by_name
  PASS  set_actor_transform
  PASS  get_actor_properties
  PASS  delete_actor

[4] Blueprint Operations
  PASS  create_blueprint
  PASS  add_component
  PASS  compile_blueprint

[5] Blueprint Nodes
  PASS  add_event_node
  PASS  find_nodes

[6] Error Handling
  PASS  unknown_command -> error
  PASS  missing_params -> error

==================================================
  Total: 14  |  PASS: 14  |  FAIL: 0  |  SKIP: 0
==================================================
```

---

## 第 3 层：集成测试

基于 pytest，拥有完整的 fixture 管理（自动清理 Actor、追踪 Blueprint 创建）。

### 运行

```bash
# 全部集成测试
cd Python
uv run pytest tests/integration/ -v

# 只跑 Actor 测试
uv run pytest tests/integration/test_actors.py -v

# 只跑 Blueprint 测试
uv run pytest tests/integration/test_blueprints.py -v
```

### 当 UE 未运行时

所有 23 个集成测试会自动 SKIP：

```
tests/integration/test_actors.py::TestActorSpawn::test_spawn_static_mesh SKIPPED
...
============================= 23 skipped in 2.04s =============================
```

### 测试覆盖

#### test_actors.py（12 个测试）

| 测试类 | 测试项 |
|--------|--------|
| `TestActorSpawn` | StaticMesh / PointLight / Camera 生成、重名检测、未知类型检测 |
| `TestActorQuery` | 获取关卡内所有 Actor、按名称搜索 |
| `TestActorTransform` | 设置位置、完整 TRS 变换、不存在 Actor 的错误处理 |
| `TestActorDelete` | 删除已有 Actor、删除不存在 Actor 的错误处理 |

#### test_blueprints.py（11 个测试）

| 测试类 | 测试项 |
|--------|--------|
| `TestBlueprintCreate` | 创建 Actor/Pawn 蓝图、重复创建处理 |
| `TestBlueprintComponents` | 添加 StaticMesh/Camera 组件、不存在蓝图的错误处理 |
| `TestBlueprintCompile` | 编译有效蓝图、编译不存在蓝图的错误处理 |
| `TestBlueprintNodes` | 添加 BeginPlay 事件、添加变量、查找节点 |

---

## 运行所有测试

```bash
cd Python

# 全部测试（单元 + 集成）
uv run pytest tests/ -v

# 只跑不需要 UE 的测试
uv run pytest tests/ -v --ignore=tests/integration

# 带覆盖率
uv run pytest tests/ --cov --cov-report=term-missing

# 带详细超时日志
uv run pytest tests/ -v --timeout=30 --timeout-method=thread
```

---

## 关键文件

```
Python/tests/
├── __init__.py
├── conftest.py               # pytest fixtures（ue_client, actor_cleanup 等）
├── test_client.py            # UnrealTestClient — 共享 TCP 客户端
├── test_version_config.py    # 单元测试（不需要 UE）
├── smoke_test.py             # 独立冒烟测试脚本
└── integration/
    ├── __init__.py
    ├── test_actors.py        # Actor 操作集成测试
    └── test_blueprints.py    # Blueprint 操作集成测试
```

---

## UnrealTestClient API

所有测试共享 `tests/test_client.py` 中的 `UnrealTestClient`：

```python
from tests.test_client import UnrealTestClient

client = UnrealTestClient(host="127.0.0.1", port=55557, timeout=10)
```

### 核心方法

| 方法 | 说明 |
|------|------|
| `command(cmd, params)` | 发送命令，返回完整 JSON 响应 |
| `ok(cmd, params)` | 发送并断言成功，返回 `result` 字典 |
| `fail(cmd, params)` | 发送并断言失败，返回错误消息字符串 |
| `is_connected()` | 检查 UE 是否可达 |

### 便捷方法

| 方法 | 说明 |
|------|------|
| `spawn_actor(name, type, location)` | 生成 Actor |
| `delete_actor(name)` | 删除 Actor |
| `get_actors()` | 获取关卡中所有 Actor |
| `create_blueprint(name, parent_class)` | 创建蓝图 |
| `compile_blueprint(name)` | 编译蓝图 |
| `add_component(bp, type, name)` | 添加组件 |
| `engine_info()` | 获取引擎信息 |

---

## pytest Fixtures

定义在 `tests/conftest.py` 中：

| Fixture | 作用域 | 说明 |
|---------|--------|------|
| `ue_client` | session | 检查 UE 连接，不可达时 skip 整个 session |
| `client` | function | 不检查连接的客户端实例，用于单元测试 |
| `unique_name` | function | 基于测试函数名生成唯一名称 |
| `actor_cleanup` | function | 追踪并在测试结束后自动删除创建的 Actor |
| `bp_cleanup` | function | 追踪创建的蓝图（记录用，UE 资产在编辑器中持久存在） |

---

## 编写新测试

### 添加新的集成测试

```python
# tests/integration/test_new_feature.py
import pytest

class TestMyNewFeature:

    def test_basic_usage(self, ue_client):
        """直接使用 ue_client fixture，UE 未运行时自动 skip。"""
        result = ue_client.ok("my_new_command", {"param": "value"})
        assert "expected_key" in result

    def test_with_cleanup(self, ue_client, actor_cleanup):
        """使用 actor_cleanup 自动清理生成的 Actor。"""
        actor_cleanup.spawn("_Test_MyActor", "StaticMeshActor")
        result = ue_client.ok("my_command_on_actor", {"name": "_Test_MyActor"})
        assert result.get("success") is not False

    def test_error_case(self, ue_client):
        """测试错误场景，断言返回 error。"""
        error_msg = ue_client.fail("my_new_command", {"param": "invalid"})
        assert "expected error text" in error_msg.lower()
```

### 添加新的单元测试

```python
# tests/test_my_logic.py
def test_parse_something():
    """纯 Python 逻辑，不需要 UE。"""
    from tools.my_module import parse_something
    assert parse_something("input") == "expected"
```

### 在冒烟测试中添加检查

编辑 `tests/smoke_test.py` 的 `run()` 函数，追加新的 `t.check()` 调用：

```python
print("\n[7] My New Feature")
t.check("my_new_command", lambda: client.ok("my_new_command", {"param": "test"}))
```

---

## AI 辅助测试工作流

本测试基础设施的设计目标之一是让 AI 助手能快速验证代码修改。工作流如下：

1. **你启动 UE 编辑器**，加载 `MCPGameProject`
2. **告诉 AI "UE 已启动"**
3. AI 可以通过终端直接执行：
   - `uv run python tests/smoke_test.py` — 快速验证
   - `uv run pytest tests/integration/ -v` — 完整验证
   - `uv run pytest tests/integration/test_actors.py::TestActorSpawn::test_spawn_static_mesh -v` — 精确验证单个测试
4. AI 根据测试结果修改代码，再跑测试 — **形成反馈循环**

### 不需要 UE 也能做的事

- 运行所有单元测试
- 代码质量检查 (`uv run ruff check .`)
- 新增/修改 Python 工具代码并验证逻辑
- 编写新测试用例

---

## 故障排除

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ConnectionRefusedError` | UE 未启动或插件未加载 | 启动 UE，检查 Output Log 中有 `UnrealMCP` 日志 |
| `Timeout connecting` | 端口不匹配或防火墙 | 确认端口 55557，检查 Windows 防火墙 |
| 集成测试全部 SKIP | UE 未运行 | 这是正常行为，启动 UE 后重跑即可 |
| `pydantic-core` 构建失败 | Python 版本过新（3.14） | 使用 `uv venv --python 3.11` |
| Blueprint 测试残留 | 测试创建的蓝图资产不会自动删除 | 手动在 UE 中删除 `_Test_*` 开头的资产 |
| Actor 残留 | `actor_cleanup` fixture 出错 | 在 UE 中搜索并删除 `_Test_*` 开头的 Actor |
