# Unreal MCP 架构设计

## 系统总览

```
┌──────────────────────┐
│   MCP 客户端          │  Cursor / Claude Desktop / Windsurf
│   (自然语言输入)       │
└─────────┬────────────┘
          │ stdio (MCP 协议)
          ▼
┌──────────────────────┐
│   Python MCP 服务器   │  unreal_mcp_server.py
│                      │  ┌─ version_config ──── config/*.json
│   ┌── tools/ ────┐   │  │
│   │ editor_tools  │   │  ├─ schemas/ (规划中)
│   │ blueprint_*   │   │  │
│   │ node_tools    │   │  └─ tests/   (规划中)
│   │ umg_tools     │   │
│   │ project_tools │   │
│   └──────────────┘   │
└─────────┬────────────┘
          │ TCP:55557 (JSON)
          ▼
┌──────────────────────┐
│   UE C++ 插件         │  UnrealMCP (Editor Subsystem)
│                      │
│   UnrealMCPBridge    │  命令路由
│     ├── EditorCmd    │  Actor / 视口 / 引擎信息
│     ├── BlueprintCmd │  BP 创建 / 组件 / 属性
│     ├── NodeCmd      │  节点图操作
│     ├── UMGCmd       │  Widget Blueprint
│     └── ProjectCmd   │  输入映射
│                      │
│   MCPServerRunnable  │  TCP 服务线程
│   CommonUtils        │  共享工具
└──────────────────────┘
          │
          ▼
┌──────────────────────┐
│   Unreal Engine      │  Editor API / Subsystems
│   编辑器              │
└──────────────────────┘
```

---

## 三层架构

### 层 1：MCP 协议层 (Python)

**职责：** 将 MCP 协议转换为内部 TCP/JSON 命令。

- `unreal_mcp_server.py` — 入口，基于 FastMCP 实现 MCP 服务器
- `version_config.py` — 版本配置管理，控制功能开关
- `tools/*.py` — 工具模块，每个模块注册一组 `@mcp.tool()` 函数

**数据流：**

```
MCP 客户端                  Python 服务器                    UE 插件
    │                           │                              │
    │  call tool(params)        │                              │
    ├──────────────────────────►│                              │
    │                           │  TCP JSON {type, params}     │
    │                           ├─────────────────────────────►│
    │                           │                              │ (GameThread)
    │                           │  TCP JSON {status, result}   │
    │                           │◄─────────────────────────────┤
    │  tool result              │                              │
    │◄──────────────────────────┤                              │
```

**设计原则：**

- 工具函数做参数验证和默认值处理，C++ 端做实际操作
- 每个工具函数是一个独立的 MCP tool，有完整的 docstring
- 版本配置控制哪些工具被注册（低版本 UE 不注册不支持的工具）
- 工具函数之间不互相调用，都通过 `send_command` 与 UE 通信

### 层 2：通信层 (TCP + JSON)

**职责：** 跨进程传递命令和响应。

**协议格式：**

请求：
```json
{
  "type": "command_name",
  "params": {
    "param1": "value1",
    "param2": 42
  }
}
```

响应：
```json
{
  "status": "success",
  "result": {
    "key": "value"
  }
}
```

错误响应：
```json
{
  "status": "error",
  "error": "Human-readable error message"
}
```

**当前限制与改进方向：**

| 当前 | 目标 |
|------|------|
| 每个命令重建 TCP 连接 | 保持连接，仅断开时重连 |
| 单条命令逐个发送 | 支持 batch 模式 |
| 无消息边界标记 | 通过 JSON 完整性判断（已实现） |
| 无超时重试 | 可配置超时 + 自动重试 |

### 层 3：引擎操作层 (C++ 插件)

**职责：** 在 Unreal Editor 中执行实际操作。

**核心类：**

| 类 | 基类 | 职责 |
|----|------|------|
| `UUnrealMCPBridge` | `UEditorSubsystem` | 生命周期管理、命令路由 |
| `FMCPServerRunnable` | `FRunnable` | TCP 服务线程 |
| `FUnrealMCPEditorCommands` | — | Actor 操作、视口、截图、引擎信息 |
| `FUnrealMCPBlueprintCommands` | — | Blueprint 创建、组件、属性 |
| `FUnrealMCPBlueprintNodeCommands` | — | 节点图操作 |
| `FUnrealMCPUMGCommands` | — | Widget Blueprint |
| `FUnrealMCPProjectCommands` | — | 项目配置 |
| `FUnrealMCPCommonUtils` | — | 静态工具函数（JSON 解析、节点创建等） |

**线程模型：**

```
TCP 线程 (FMCPServerRunnable)
  │
  │ 接收 JSON → 解析
  │
  ├──► AsyncTask(GameThread) ──► 执行命令 ──► 返回结果
  │
  │ ◄── Future.Get() 等待结果
  │
  │ 发送响应 JSON
```

所有 UE API 调用必须在 GameThread 上执行。TCP 线程通过 `AsyncTask + TPromise/TFuture` 实现同步等待。

---

## 命令路由

### 当前机制 (if-else 链)

```cpp
if (CommandType == "get_actors_in_level" || ...)
    ResultJson = EditorCommands->HandleCommand(CommandType, Params);
else if (CommandType == "create_blueprint" || ...)
    ResultJson = BlueprintCommands->HandleCommand(CommandType, Params);
// ... 每新增命令需在此添加
```

**问题：** 新增命令需要修改 Bridge (路由) + Commands (处理) + Python (工具) 三处。

### 目标机制 (注册表)

```cpp
// Commands 类构造时自注册
FUnrealMCPEditorCommands::FUnrealMCPEditorCommands(FCommandRegistry& Registry)
{
    Registry.Register("get_actors_in_level", [this](auto P){ return HandleGetActorsInLevel(P); });
    Registry.Register("spawn_actor",         [this](auto P){ return HandleSpawnActor(P); });
    // ...
}

// Bridge 执行时直接查表
FString UUnrealMCPBridge::ExecuteCommand(const FString& Type, ...)
{
    auto Handler = Registry.Find(Type);
    if (Handler) return Handler(Params);
    return CreateErrorResponse("Unknown command: " + Type);
}
```

**收益：** 新增命令只需在 Commands 类中添加一行注册 + Handler 实现，Bridge 不再需要修改。

---

## 版本配置系统

```
Python/config/
  ├── default.json   ← 基础配置（全功能）
  ├── ue5.3.json     ← 5.3 覆盖（禁用 Widget BP 等）
  ├── ue5.4.json     ← 5.4 覆盖（禁用 BlueprintEditorLibrary）
  └── ue5.5.json     ← 5.5 覆盖（全功能）
```

**加载顺序：** default.json → ue{version}.json 深度合并

**版本确定优先级：**
1. CLI 参数 `--ue-version 5.4`
2. 环境变量 `UE_VERSION`
3. 自动检测（启动时向引擎发送 `get_engine_info`）
4. 默认值 `5.5`

**功能控制：** 通过 `config.has_feature("widget_blueprint")` 决定是否注册对应工具。

---

## 模块扩展指南

### 添加一个新命令的完整流程

以添加 `create_material` 命令为例：

**1. C++ 端 — 创建或扩展 Commands 类**

```
Public/Commands/UnrealMCPAssetCommands.h    (新文件或已有)
Private/Commands/UnrealMCPAssetCommands.cpp
```

在 Commands 类中添加 Handler：
```cpp
TSharedPtr<FJsonObject> HandleCreateMaterial(const TSharedPtr<FJsonObject>& Params);
```

并在构造函数中注册（注册表机制实现后）：
```cpp
Registry.Register("create_material", ...);
```

**2. Python 端 — 添加工具函数**

在 `tools/asset_tools.py` 中：
```python
@mcp.tool()
def create_material(ctx: Context, name: str, path: str = "/Game/Materials") -> Dict[str, Any]:
    """Create a new material asset. ..."""
    response = unreal.send_command("create_material", {"name": name, "path": path})
    return response
```

在 `unreal_mcp_server.py` 中注册模块。

**3. Schema（规划中）**

在 `schemas/create_material.json` 中定义参数规范。

**4. 测试**

在 `tests/integration/test_assets.py` 中编写集成测试。

**5. 文档**

在 `Docs/Tools/` 中更新对应文档，或由 Schema 自动生成。

---

## 关键设计决策

### 为什么不用 HTTP/REST？

TCP Socket 比 HTTP 少一层协议开销。MCP 协议本身通过 stdio 通信，Python 服务器和 UE 之间是进程间通信，不需要 HTTP 的路由、Header、Content-Type 等开销。JSON over TCP 是最简单有效的方式。

### 为什么不用 gRPC/Protobuf？

引入 gRPC 需要在 UE C++ 端编译 Protobuf 库，增加构建复杂度。当前命令数量和数据量下 JSON 性能完全足够。如果未来命令数量到 500+ 或者需要传输大量二进制数据（纹理/网格），可以考虑迁移。

### 为什么 Blueprint 节点操作不在 Python 端做？

Python 端无法直接操作 UE 内部的 `UEdGraph`、`UK2Node` 等 C++ 对象。所有蓝图图形操作必须在 C++ 插件中完成。Python 端只负责参数验证和 MCP 协议转换。

### 为什么用 Editor Subsystem？

`UEditorSubsystem` 是 UE 5 的标准编辑器扩展机制，自动跟随编辑器生命周期（启动时 Initialize、关闭时 Deinitialize），不需要手动管理单例或 Module 生命周期。

### 为什么 CommonUtils 是静态类而不是基类？

命令处理器之间没有继承关系，它们是平级的模块。共享功能通过静态工具类提供，比继承更灵活，不会产生菱形继承等问题。
