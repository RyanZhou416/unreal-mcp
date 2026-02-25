# 版本兼容性

## 支持矩阵

| 特性 | UE 5.3 | UE 5.4 | UE 5.5 | UE 5.7 |
|------|--------|--------|--------|--------|
| Actor CRUD | 支持 | 支持 | 支持 | 支持 |
| Blueprint 创建/编译 | 支持 | 支持 | 支持 | 支持 |
| Blueprint 节点操作 | 支持 | 支持 | 支持 | 支持 |
| Blueprint 变量 | 支持 | 支持 | 支持 | 支持 |
| 组件操作 | 支持 | 支持 | 支持 | 支持 |
| EnhancedInput | 支持 | 支持 | 支持 | 支持 |
| UMG Widget Blueprint | 不支持 | 支持 | 支持 | 支持 |
| BlueprintEditorLibrary | 不支持 | 不支持 | 支持 | 支持 |
| Input Mapping | 支持 | 支持 | 支持 | 支持 |
| 截图 | 支持 | 支持 | 支持 | 支持 |

### Build.cs 行为差异

| 项目 | UE 5.3 | UE 5.4 | UE 5.5+ |
|------|--------|--------|---------|
| IWYU 配置 | `bEnforceIWYU` | `bEnforceIWYU` | `IWYUSupport` enum |
| BlueprintEditorLibrary 模块 | 不存在 | 不存在 | 可用 |
| UMGEditor 模块 | 不存在 | 可用 | 可用 |

---

## C++ 版本适配策略

采用**单一代码库 + 兼容性 Shim 层**：所有版本差异集中封装在 `UnrealMCPCompat.h` 中，业务代码不直接处理版本分支。

### 第一层：Build.cs 版本检测

[UnrealMCP.Build.cs](../UE5/MCPHost/Plugins/UnrealMCP/Source/UnrealMCP/UnrealMCP.Build.cs) 使用 `BuildVersion.TryRead` 在编译期检测引擎版本，完成两项工作：

**1. 条件依赖**

```csharp
int EngineMajor = 5, EngineMinor = 5;
BuildVersion OutVersion;
if (BuildVersion.TryRead(BuildVersion.GetDefaultFileName(), out OutVersion))
{
    EngineMajor = OutVersion.MajorVersion;
    EngineMinor = OutVersion.MinorVersion;
}
bool bIsUE55OrLater = (EngineMajor > 5) || (EngineMajor == 5 && EngineMinor >= 5);

if (bIsUE55OrLater)
{
    PrivateDependencyModuleNames.Add("BlueprintEditorLibrary");
    PublicDefinitions.Add("WITH_BLUEPRINT_EDITOR_LIBRARY=1");
}
else
{
    PublicDefinitions.Add("WITH_BLUEPRINT_EDITOR_LIBRARY=0");
}
```

**2. 自适应 IWYU**

UE 5.5 将 `bEnforceIWYU` 替换为 `IWYUSupport` enum。通过反射在任何 UE 5.x 上编译：

```csharp
var iwyu = GetType().GetProperty("IWYUSupport");
if (iwyu != null)
{
    var fullValue = Enum.Parse(iwyu.PropertyType, "Full");
    iwyu.SetValue(this, fullValue);
}
else
{
    var enforce = GetType().GetProperty("bEnforceIWYU");
    if (enforce != null) enforce.SetValue(this, true);
}
```

### 第二层：兼容性头文件 UnrealMCPCompat.h

所有 UE API 版本差异封装在一个头文件中。业务代码只调用 shim 函数，不感知版本。

文件位置：`Plugins/UnrealMCP/Source/UnrealMCP/Public/UnrealMCPCompat.h`

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Misc/EngineVersionComparison.h"
#include "UObject/FindObject.h"
#include "ImageUtils.h"

// ── 类查找 ─────────────────────────────────────────────────────
// ANY_PACKAGE 在 UE 5.7 中移除，替代为 FindFirstObject
template<typename T>
FORCEINLINE T* MCPFindClass(const TCHAR* Name)
{
#if UE_VERSION_OLDER_THAN(5, 7, 0)
    return FindObject<T>(ANY_PACKAGE, Name);
#else
    return FindFirstObject<T>(Name, EFindFirstObjectOptions::EnsureIfAmbiguous);
#endif
}

// ── 截图压缩 ───────────────────────────────────────────────────
// 5.7: CompressImageArray 弃用 + PNGCompressImageArray 改用 TArray64
#if UE_VERSION_OLDER_THAN(5, 7, 0)
FORCEINLINE void MCPCompressImage(int32 Width, int32 Height,
    const TArray<FColor>& SrcBitmap, TArray<uint8>& DstCompressed)
{
    FImageUtils::CompressImageArray(Width, Height, SrcBitmap, DstCompressed);
}
#else
FORCEINLINE void MCPCompressImage(int32 Width, int32 Height,
    const TArray<FColor>& SrcBitmap, TArray64<uint8>& DstCompressed)
{
    FImageUtils::PNGCompressImageArray(Width, Height, SrcBitmap, DstCompressed);
}
#endif
```

### 第三层：UE 内置版本宏

来自 `Misc/EngineVersionComparison.h`（UE 5.0+ 内置），是条件编译的基础工具。

| 宏 | 含义 | 示例 |
|----|------|------|
| `UE_VERSION_OLDER_THAN(M, m, p)` | 当前版本 < 指定版本 | `#if UE_VERSION_OLDER_THAN(5, 7, 0)` |
| `UE_VERSION_NEWER_THAN(M, m, p)` | 当前版本 > 指定版本 | `#if UE_VERSION_NEWER_THAN(5, 4, 0)` |
| `!UE_VERSION_OLDER_THAN(M, m, p)` | 当前版本 >= 指定版本 | `#if !UE_VERSION_OLDER_THAN(5, 5, 0)` |

**规则：**

- 在 `UnrealMCPCompat.h` 中使用这些宏封装差异
- 业务代码（Commands/*.cpp）中**禁止**直接使用 `UE_VERSION_*` 或 `ENGINE_MINOR_VERSION`
- 需要新的版本分支时，在 `UnrealMCPCompat.h` 中添加 shim 函数

### 业务代码调用方式

修改前（版本差异散落在业务代码中）：

```cpp
// UnrealMCPBlueprintCommands.cpp — 不推荐
ComponentClass = FindFirstObject<UClass>(*ComponentType,
    EFindFirstObjectOptions::EnsureIfAmbiguous);
```

修改后（通过 shim 层调用）：

```cpp
// UnrealMCPBlueprintCommands.cpp — 推荐
#include "UnrealMCPCompat.h"
ComponentClass = MCPFindClass<UClass>(*ComponentType);
```

---

## 已知 API 变更清单

新发现 API 差异时，必须更新此表格。

| UE 版本 | 变更内容 | 影响文件 | 适配方式 |
|---------|----------|----------|----------|
| 5.5 | `bEnforceIWYU` → `IWYUSupport` enum | Build.cs | 反射动态设置 |
| 5.5 | `BlueprintEditorLibrary` 模块引入 | Build.cs | `bIsUE55OrLater` 条件依赖 |
| 5.7 | `ANY_PACKAGE` 移除 | BlueprintCommands, BlueprintNodeCommands | `MCPFindClass<T>()` shim |
| 5.7 | `FImageUtils::CompressImageArray` 弃用 | EditorCommands | `MCPCompressImage()` shim |
| 5.7 | `PNGCompressImageArray` 签名改为 `TArray64<uint8>&` | EditorCommands | 输出变量使用 `TArray64<uint8>` |
| 5.7 | `WhitelistPlatforms` → `PlatformAllowList` | UnrealMCP.uplugin | 直接使用新名称（5.3+ 兼容） |
| 5.7 | 全局变量名隐藏引擎头文件变量 (C4459→Error) | MCPServerRunnable | 重命名变量避免冲突 |

---

## 插件源码管理

### 当前问题

插件代码存在两份拷贝，容易漂移：

```
MCPGameProject/Plugins/UnrealMCP/    ← 旧 5.5 项目
UE5/MCPHost/Plugins/UnrealMCP/       ← 新 5.7 项目
```

### 目标结构

将插件源码提升为仓库级独立目录，各 UE 项目通过引用使用：

```
unreal-mcp/
├── Plugins/UnrealMCP/               ← 唯一源码位置
├── Python/
├── Docs/
├── UE5/MCPHost/                     ← 通过 symlink 引用 Plugins/
└── MCPGameProject/                  ← 通过 symlink 引用 Plugins/（可废弃）
```

### Symlink 创建方式

Windows（管理员 PowerShell）：

```powershell
New-Item -ItemType Junction `
    -Path "C:\Project\unreal-mcp\UE5\MCPHost\Plugins\UnrealMCP" `
    -Target "C:\Project\unreal-mcp\Plugins\UnrealMCP"
```

macOS / Linux：

```bash
ln -s ../../Plugins/UnrealMCP UE5/MCPHost/Plugins/UnrealMCP
```

### 替代方案：.uproject AdditionalPluginDirectories

在 `.uproject` 中指定插件搜索路径（UE 5.0+ 支持）：

```json
{
    "AdditionalPluginDirectories": [
        "../../Plugins"
    ]
}
```

此方式不需要 symlink，但部分 IDE（Rider）可能需要重新索引。

---

## Python 版本配置规范

Python 侧使用运行时版本检测，配置系统位于 `Python/version_config.py`。

### 配置文件结构

```
Python/config/
├── default.json     ← 基础配置（所有功能开启）
├── ue5.3.json       ← 5.3 覆盖（禁用 UMG/BlueprintEditorLibrary）
├── ue5.4.json       ← 5.4 覆盖（禁用 BlueprintEditorLibrary）
├── ue5.5.json       ← 5.5 覆盖（所有功能开启）
└── ue5.7.json       ← 5.7 覆盖（所有功能开启）
```

### 版本检测优先级

1. 命令行参数 `--ue-version 5.7`
2. 环境变量 `UE_VERSION=5.7`
3. 运行时自动检测（通过 `get_engine_info` TCP 命令）
4. `DEFAULT_VERSION`（当前为 `"5.7"`）

### 功能标志控制

工具模块的条件注册由 `has_feature()` 控制：

```python
if config.has_feature("widget_blueprint"):
    register_umg_tools(mcp, config)

if config.has_feature("input_mapping"):
    register_project_tools(mcp, config)
```

### 功能标志命名规范

| 类型 | 命名 | 示例 |
|------|------|------|
| 模块级开关 | `{module}_editor` | `umg_editor` |
| API 级开关 | `{feature_name}` | `blueprint_editor_library` |
| 命令级开关 | `{command_category}` | `blueprint_nodes`, `widget_blueprint` |

---

## 跨版本测试策略

### 测试层级

| 层级 | 需要 UE | 验证内容 |
|------|---------|----------|
| 单元测试 | 否 | Python 版本配置逻辑（各版本功能标志正确性） |
| 冒烟测试 | 是 | 核心链路通畅（连接、Actor、Blueprint、节点） |
| 集成测试 | 是 | 所有命令的完整功能和边界情况 |
| 编译验证 | 否（需引擎源码） | C++ 代码在各版本下编译通过 |

### 本地多版本测试

如果本地安装了多个 UE 版本：

1. 为每个版本创建独立 UE 项目（symlink 同一份插件源码）
2. 分别编译、启动编辑器
3. 用 `--ue-version` 参数指定版本运行测试：

```bash
uv run python tests/smoke_test.py                     # 默认 5.7
uv run python tests/smoke_test.py --port 55558         # 如果不同版本用不同端口
```

### CI 矩阵（理想状态）

```yaml
strategy:
  matrix:
    ue-version: ["5.3", "5.4", "5.5", "5.7"]
steps:
  - name: Build plugin
    run: UnrealBuildTool MCPHost Development Win64
  - name: Run unit tests
    run: uv run pytest tests/test_version_config.py -v
```

### 版本回归检查清单

每次修改 C++ 代码后，检查：

- [ ] `UnrealMCPCompat.h` 中的 shim 函数是否覆盖了本次改动涉及的 API
- [ ] Build.cs 中的条件依赖是否需要更新
- [ ] Python `config/` 中的功能标志是否需要调整
- [ ] 已知 API 变更清单是否需要新增条目

---

## 新增 UE 版本支持 SOP

当需要支持新的 UE 版本（如 5.8）时，按以下步骤执行：

### 步骤 1：编译验证

1. 创建新 UE 项目，symlink 插件
2. 编译，收集所有编译错误和弃用警告
3. 将 API 差异记录到「已知 API 变更清单」

### 步骤 2：更新 Compat Shim

1. 在 `UnrealMCPCompat.h` 中为每个 API 差异添加 shim 函数
2. 更新业务代码调用 shim 函数
3. 确保旧版本编译不受影响

### 步骤 3：更新 Build.cs

1. 检查是否有新模块需要条件引入
2. 检查 IWYU 或其他构建系统变更
3. 更新 `PublicDefinitions` 中的版本宏

### 步骤 4：更新 Python 配置

1. 创建 `Python/config/ue5.8.json`
2. 在 `version_config.py` 的 `SUPPORTED_VERSIONS` 中添加 `"5.8"`
3. 评估是否需要更新 `DEFAULT_VERSION`
4. 在 `mcp.json` 中添加对应的服务器配置

### 步骤 5：更新测试

1. 在 `test_version_config.py` 中添加新版本的功能标志测试
2. 运行全量单元测试确认不回归
3. 启动新版本 UE 运行冒烟测试和集成测试

### 步骤 6：更新文档

1. 更新本文档的「支持矩阵」
2. 更新 `BlueprintCoverage.md` 中的版本覆盖情况
3. 更新 `ROADMAP.md` 如有需要

---

## 禁止事项

- 禁止在 Commands/*.cpp 中直接使用 `UE_VERSION_OLDER_THAN` / `ENGINE_MINOR_VERSION`
- 禁止在 Commands/*.cpp 中直接写版本特定 API（必须通过 shim）
- 禁止手写 `#if ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 7` 式比较
- 禁止在不同 UE 项目中维护不同版本的插件源码
- 禁止新增功能标志时不同步更新所有版本 JSON 配置
