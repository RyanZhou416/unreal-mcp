# 贡献指南

## 开发环境搭建

### 前置要求

- Unreal Engine 5.3+ (推荐 5.5)
- Visual Studio 2022 / Rider (C++ 开发)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Python 包管理)
- Git

### 首次搭建

```bash
# 1. 克隆仓库
git clone <repo-url>
cd unreal-mcp

# 2. Python 环境
cd Python
uv venv --python 3.11        # Python 3.14 暂不支持 pydantic-core
uv pip install -e ".[dev]"

# 3. C++ 项目
# 右键 MCPGameProject/MCPGameProject.uproject → Generate Visual Studio project files
# 打开 .sln → 配置 Development Editor → 构建

# 4. 验证（不需要 UE）
uv run pytest tests/ -v --ignore=tests/integration

# 5. 完整验证（启动 UE 后）
uv run python tests/smoke_test.py     # 冒烟测试
uv run pytest tests/ -v               # 全部测试
```

---

## 命名规范

### Python

| 元素 | 风格 | 示例 |
|------|------|------|
| 模块文件 | snake_case | `blueprint_tools.py` |
| 函数/方法 | snake_case | `create_blueprint()` |
| 参数 | snake_case | `blueprint_name` |
| 类 | PascalCase | `VersionConfig` |
| 常量 | UPPER_SNAKE | `DEFAULT_VERSION` |
| MCP 工具名 | snake_case (自动从函数名) | `create_blueprint` |

### C++

| 元素 | 风格 | 示例 |
|------|------|------|
| 类 | F/U 前缀 + PascalCase | `FUnrealMCPEditorCommands`、`UUnrealMCPBridge` |
| 函数 | PascalCase | `HandleCreateBlueprint()` |
| 成员变量 | PascalCase (可加 b 前缀) | `bIsRunning`、`ServerAddress` |
| 命令名 (字符串) | snake_case | `"create_blueprint"` |
| 宏 | UPPER_SNAKE | `UNREALMCP_PLUGIN_VERSION` |
| Log Category | Log + PascalCase | `LogUnrealMCP` |

### 命令参数命名

**全局统一规则：**

- 所有命令中引用蓝图的参数统一用 `blueprint_name`（不用 `widget_name`、`bp_name` 等变体）
- 位置用 `location` (List[float])，旋转用 `rotation` (List[float])，缩放用 `scale` (List[float])
- 组件名用 `component_name`，组件类型用 `component_type`
- 属性名用 `property_name`，属性值用 `property_value`
- 节点 ID 用 `node_id`（返回时）或 `source_node_id` / `target_node_id`（引用时）
- Pin 名用 `source_pin` / `target_pin`

---

## 新增命令的标准流程

### 第一步：C++ Handler

1. 在对应的 Commands 头文件中声明 Handler：

```cpp
// Public/Commands/UnrealMCPBlueprintCommands.h
private:
    TSharedPtr<FJsonObject> HandleNewCommand(const TSharedPtr<FJsonObject>& Params);
```

2. 在 Commands 实现文件中添加实现：

```cpp
// Private/Commands/UnrealMCPBlueprintCommands.cpp
TSharedPtr<FJsonObject> FUnrealMCPBlueprintCommands::HandleNewCommand(
    const TSharedPtr<FJsonObject>& Params)
{
    // 1. 参数解析
    FString Name;
    if (!Params->TryGetStringField(TEXT("name"), Name))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // 2. 执行操作
    // ...

    // 3. 返回结果
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetStringField(TEXT("name"), Name);
    return ResultObj;
}
```

3. 在 `HandleCommand` 中注册路由（当前 if-else 方式，后续会改为注册表）：

```cpp
else if (CommandType == TEXT("new_command"))
{
    return HandleNewCommand(Params);
}
```

4. 在 `UnrealMCPBridge.cpp` 的 `ExecuteCommand` 中添加路由。

### 第二步：Python 工具

在 `tools/` 对应模块中添加工具函数：

```python
@mcp.tool()
def new_command(
    ctx: Context,
    name: str,
    option: str = "default_value"
) -> Dict[str, Any]:
    """一句话描述这个工具的功能。

    Args:
        ctx: MCP 上下文
        name: 操作目标的名称
        option: 可选参数说明，默认为 "default_value"

    Returns:
        操作结果字典

    Example:
        new_command(name="MyThing", option="custom")
    """
    from unreal_mcp_server import get_unreal_connection

    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}

        response = unreal.send_command("new_command", {
            "name": name,
            "option": option,
        })
        return response or {}

    except Exception as e:
        logger.error(f"Error in new_command: {e}")
        return {"success": False, "message": str(e)}
```

### 第三步：测试

使用 `UnrealTestClient` 编写集成测试（详见 [Testing.md](Testing.md)）：

```python
# tests/integration/test_new_feature.py
class TestNewCommand:

    def test_basic(self, ue_client):
        result = ue_client.ok("new_command", {"name": "Test"})
        assert result["name"] == "Test"

    def test_missing_param(self, ue_client):
        ue_client.fail("new_command", {})
```

### 第四步：文档

在 `Docs/Tools/` 中更新对应文档。

---

## 工具函数规范 (@mcp.tool)

遵循 `.cursor/rules/tools.mdc` 中的规则：

1. **参数类型不得使用** `Any`、`object`、`Optional[T]`、`Union[T]`
2. **有默认值的参数** 直接写 `param: Type = default`，不要写 `param: Type | None = None`
3. **必须有 docstring**，包含参数说明和输入示例
4. **默认值处理** 在函数体内进行，不要依赖 Python 的 None 传播

```python
# 正确
def my_tool(ctx: Context, name: str, location: List[float] = [0, 0, 0]) -> Dict[str, Any]:

# 错误
def my_tool(ctx: Context, name: str, location: Optional[List[float]] = None) -> Dict[str, Any]:
```

---

## 响应格式规范

### C++ 端

成功响应 — Handler 返回结果对象，Bridge 包装为：
```json
{"status": "success", "result": { ... }}
```

错误响应 — Handler 返回 `CreateErrorResponse()`：
```json
{"status": "error", "error": "Human-readable error message"}
```

### Python 端

工具函数直接返回从 C++ 收到的响应。连接失败时返回：
```python
{"success": False, "message": "描述信息"}
```

---

## 代码质量

### Python

```bash
# 检查代码质量
cd Python
uv run ruff check .

# 自动修复
uv run ruff check --fix .

# 格式化
uv run ruff format .

# 运行所有测试
uv run pytest tests/ -v

# 只跑单元测试（不需要 UE）
uv run pytest tests/ -v --ignore=tests/integration

# 带覆盖率
uv run pytest tests/ --cov --cov-report=term-missing
```

> 完整的测试说明见 [Testing.md](Testing.md)

### C++

- 使用 UE 推荐的代码风格
- 所有 `UE_LOG` 使用 `LogUnrealMCP` Category（待实现）
- 函数长度不超过 100 行，超过则拆分
- 每个 public 函数必须有注释

---

## Git 工作流

### 分支策略

- `main` — 稳定版本，只接受 PR 合入
- `develop` — 开发主线
- `feature/xxx` — 功能分支
- `fix/xxx` — 修复分支
- `release/vX.Y.Z` — 发布分支

### Commit 消息格式

```
<type>(<scope>): <description>

<body>
```

**type：**
- `feat` — 新功能
- `fix` — 修复
- `refactor` — 重构（不改变功能）
- `docs` — 文档
- `test` — 测试
- `chore` — 构建/工具

**scope：**
- `python` — Python 端
- `cpp` — C++ 端
- `config` — 配置
- `tools` — MCP 工具
- `bridge` — 通信层

**示例：**
```
feat(cpp): add Branch node creation support

Implement K2Node_IfThenElse creation in BlueprintNodeCommands.
Register as "add_blueprint_branch_node" command.
```

### PR 要求

- 有清晰的描述说明改了什么和为什么
- 通过所有 CI 检查（lint + 单元测试）
- 新增命令必须包含集成测试（`tests/integration/`）
- 新增命令必须在冒烟测试中添加检查（`tests/smoke_test.py`）
- 新增命令必须更新文档（`Docs/Tools/`）
