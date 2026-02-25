# 技术栈选型

选型优先级：**效果 > 新技术 > 性能**。

即：首先保证功能正确、开发体验好，其次选择现代化的工具链，最后才考虑运行时性能优化。

---

## 已确定的技术栈

这些是项目的核心依赖，不会变更。

| 层 | 技术 | 版本 | 选择原因 |
|----|------|------|---------|
| 引擎 | Unreal Engine | 5.3 - 5.5+ | 目标平台 |
| C++ 构建 | UnrealBuildTool | 随 UE 版本 | UE 唯一构建系统 |
| MCP 协议 | FastMCP | >=0.2.0 | MCP Python SDK 中最简洁的实现，装饰器风格注册 |
| Python 运行时 | Python | >=3.10 | FastMCP 要求 |
| 包管理 | uv | 最新 | Rust 实现，比 pip 快 10-100x，现代 Python 标准 |
| 进程间通信 | TCP + JSON | — | 简单、可调试、跨语言通用 |
| 版本控制 | Git | — | 行业标准 |

---

## 新引入的技术

### Python 端

#### Pydantic v2 — 数据校验与 Schema 生成

**用途：** 命令参数校验、响应格式定义、自动生成 JSON Schema。

**为什么选它而不是 jsonschema：**
- Pydantic v2 基于 Rust (pydantic-core) 重写，校验速度比 v1 快 5-50 倍
- 类型定义即文档，一个 Model 同时是校验器、序列化器和 Schema 生成器
- FastMCP 本身依赖 Pydantic，零额外依赖
- 比原始 jsonschema 库开发体验好得多——写 Python class 而不是写 JSON

**效果示例：**
```python
from pydantic import BaseModel, Field

class CreateBlueprintParams(BaseModel):
    name: str = Field(description="Blueprint 名称")
    parent_class: str = Field(default="Actor", description="父类名称")

# 自动校验
params = CreateBlueprintParams(name="MyBP")

# 自动生成 JSON Schema
schema = CreateBlueprintParams.model_json_schema()
```

#### pytest — 测试框架

**为什么选 pytest 而不是 unittest：**
- fixture 机制比 setUp/tearDown 更灵活，可以组合和参数化
- 断言直接用 `assert`，不需要记 `assertEqual` / `assertTrue` 等方法
- 插件生态丰富（pytest-asyncio, pytest-timeout, pytest-cov）
- 社区事实标准，几乎所有现代 Python 项目都使用

**关键插件：**

| 插件 | 用途 |
|------|------|
| pytest-asyncio | 异步测试支持 |
| pytest-timeout | 防止测试挂死（UE 连接超时场景） |
| pytest-cov | 覆盖率报告 |

#### ruff — 代码质量

**为什么选 ruff 而不是 flake8 + black + isort：**
- Rust 实现，一个工具替代 flake8、black、isort、pyupgrade 四个
- 比 flake8 快 10-100x
- 2024-2025 年 Python 社区增长最快的工具
- 零配置即可使用，在 `pyproject.toml` 中统一配置

```toml
[tool.ruff]
target-version = "py310"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP"]
```

### C++ 端

#### UE Automation Framework — C++ 测试

**为什么用 UE 自带的而不是 Catch2/GoogleTest：**
- 可以在编辑器中直接运行测试（Session Frontend → Automation）
- 能访问完整的 UE API（GEditor, GWorld 等）
- 支持 Latent 测试（等待异步操作完成）
- 不需要额外的构建配置

**效果示例：**
```cpp
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FMCPCommandRegistryTest,
    "UnrealMCP.Registry.RegisterAndFind",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter
)

bool FMCPCommandRegistryTest::RunTest(const FString& Parameters)
{
    FCommandRegistry Registry;
    Registry.Register("test_cmd", [](auto) { return MakeShared<FJsonObject>(); });
    TestTrue("Command should be found", Registry.HasCommand("test_cmd"));
    return true;
}
```

#### clang-format — C++ 代码格式化

UE 社区标准格式化工具。配合 `.clang-format` 文件统一代码风格。

### 文档与 CI

#### MkDocs Material — 文档站点

**为什么选它而不是 Sphinx 或纯 Markdown：**
- Material 主题是目前最美观的开源文档主题
- 原生支持 Markdown（不需要学 reStructuredText）
- 支持搜索、暗色模式、移动端
- 从现有 Docs/*.md 零迁移成本

**但在早期阶段，先只写 Markdown 文件即可，后期需要站点时再引入 MkDocs。**

#### GitHub Actions — CI/CD

**工作流设计：**

| 工作流 | 触发条件 | 内容 |
|--------|---------|------|
| `lint.yml` | PR / Push | ruff check + ruff format --check |
| `test-python.yml` | PR / Push | pytest 单元测试（不需要 UE） |
| `test-integration.yml` | 手动触发 | 集成测试（需要 UE，self-hosted runner） |
| `docs.yml` | Push to main | 构建文档站点（MkDocs，Phase 5 引入） |
| `release.yml` | Tag push | 版本发布 |

---

## 不采用的方案及原因

| 方案 | 不采用的原因 |
|------|------------|
| **gRPC / Protobuf** | 需要在 UE C++ 中编译 Protobuf，构建复杂度大增。当前 JSON 命令数量和体积下无性能瓶颈。效果不会更好，只是更快。 |
| **WebSocket** | 比 TCP 多一层握手和帧协议，本地通信场景下无收益。ws:// 的优势是穿越网络/代理，但我们是同机通信。 |
| **HTTP REST** | 每个命令一个 HTTP 请求的开销（建连、Header 解析）远大于 TCP 直连。无法实现服务端推送。 |
| **MessagePack** | 性能比 JSON 好 2-3x，但失去可读性。调试时无法直接看消息内容。性能不是当前瓶颈。 |
| **Sphinx** | reStructuredText 学习成本高，配置复杂。Markdown 写文档更自然。 |
| **Catch2 / GoogleTest** | 需要额外构建配置，无法访问 UE Editor API（GEditor 等）。UE Automation Framework 能做到的事它们做不到。 |
| **flake8 + black + isort** | 三个工具各自配置、各自运行。ruff 一个工具全替代，速度还快 100 倍。 |
| **Poetry** | 已经用 uv，Poetry 的锁文件机制对 MCP 服务器场景过重。uv 更现代更快。 |

---

## 依赖管理

### Python 依赖 (pyproject.toml)

```toml
[project]
dependencies = [
  "mcp[cli]>=1.4.1",
  "fastmcp>=0.2.0",
  "pydantic>=2.6.1",       # 已有
  "uvicorn",
  "fastapi",
  "requests",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.24",
  "pytest-timeout>=2.3",
  "pytest-cov>=5.0",
  "ruff>=0.8",
]
```

### C++ 依赖 (Build.cs)

所有依赖来自 UE 引擎模块，不引入第三方 C++ 库。这是刻意的选择——UE 插件引入第三方库会显著增加构建和分发复杂度。

---

## 技术决策记录 (ADR) 格式

后续重要技术决策使用以下格式记录：

```markdown
### ADR-001: 标题

**状态：** 已采纳 / 已拒绝 / 已废弃

**背景：** 为什么需要做这个决策

**决策：** 我们决定...

**原因：**
- 理由 1
- 理由 2

**后果：**
- 正面影响
- 需要注意的风险
```
