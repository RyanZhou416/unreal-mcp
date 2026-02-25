# Unreal MCP 路线图

本文档定义了 unreal-mcp 从实验性原型演进为**完整支持 UE5 全部蓝图能力**的标准化项目的长期路线图。

---

## 当前状态 (v0.1.0)

已实现 31 个 MCP 工具，覆盖：

| 模块 | 工具数 | 范围 |
|------|-------|------|
| Editor | 9 | Actor CRUD、Transform、属性、视口、截图 |
| Blueprint 结构 | 7 | 创建 BP、添加组件、设置属性/物理、编译 |
| Blueprint 节点 | 8 | 6 种 K2Node（Event/CallFunction/InputAction/VariableGet/Self/InputAction） |
| UMG | 6 | Widget Blueprint 创建、TextBlock、Button |
| 项目 | 1 | InputMapping |

**核心缺失：** 控制流节点、类型转换、SpawnActor、自定义函数、大部分 Widget 类型、资产管理、关卡管理、Animation Blueprint、Level Blueprint。

---

## Phase 0：基础设施重构 (2-3 周)

**目标：** 把地基打牢——让后续每一个功能扩展都只需要写 Handler 而不需要改框架。

### 0.1 命令注册表

将 `UnrealMCPBridge::ExecuteCommand()` 中的 if-else 链替换为 `TMap<FString, CommandHandler>` 注册表。每个 Commands 类在构造时注册自己的命令，新增命令不再需要修改 Bridge。

### 0.2 日志体系

- C++ 端：声明 `DECLARE_LOG_CATEGORY_EXTERN(LogUnrealMCP, Log, All)` 替代 `LogTemp`
- Python 端：统一 logger 配置（已有基础，需要标准化格式）

### 0.3 参数与响应标准化

- 统一参数命名（如 `widget_name` 全部改为 `blueprint_name`）
- 统一响应结构：`{ "status": "success|error", "result": {...}, "error": "..." }`
- 引入 JSON Schema，对每个命令定义输入输出规范

### 0.4 测试框架

- 提取 `TestClient` 共享类
- 建立 pytest 框架（conftest.py + fixture）
- 编写 version_config 单元测试
- 编写基础集成测试（Actor 操作）

### 0.5 TCP 连接优化

- C++ 端保持连接（不再每次命令后关闭 socket）
- Python 端连接复用和自动重连
- 支持 batch 命令模式

### 交付物

- [ ] 命令注册表机制
- [ ] 日志 Category
- [ ] 参数命名统一
- [ ] 响应格式统一
- [ ] JSON Schema 基础（核心命令）
- [ ] pytest 框架 + 10+ 测试用例
- [ ] TCP 连接保持

---

## Phase 1：Blueprint 节点补全 (3-4 周)

**目标：** 覆盖 90% 的常见蓝图场景。

### 1.1 P0 控制流节点

| 节点 | K2Node 类型 | 说明 |
|------|------------|------|
| Branch | `K2Node_IfThenElse` | 条件分支，蓝图中最核心的控制流 |
| Sequence | MacroInstance | 顺序执行多个分支 |
| ForEachLoop | MacroInstance | 遍历数组 |
| DoOnce | MacroInstance | 只执行一次 |
| Delay | `K2Node_CallFunction` (Delay) | 延迟执行 |
| FlipFlop | MacroInstance | 交替执行 |
| Gate | MacroInstance | 门控 |

### 1.2 P0 高频节点

| 节点 | 方式 | 说明 |
|------|------|------|
| SpawnActor | `K2Node_SpawnActorFromClass` | 运行时生成 Actor |
| Cast To | `K2Node_DynamicCast` | 类型转换 |
| Variable Set | 暴露已有 CommonUtils | 设置蓝图变量值 |
| PrintString | CallFunction | 调试输出 |
| MakeArray | `K2Node_MakeArray` | 创建数组 |
| Array 操作 | CallFunction | Add/Remove/Get/Set/Length |
| 数学运算 | CallFunction (KismetMathLibrary) | Add/Subtract/Multiply/Divide/Clamp/Lerp |
| 比较运算 | CallFunction | Equal/NotEqual/Greater/Less |
| 逻辑运算 | CallFunction | AND/OR/NOT |

### 1.3 函数系统

- 创建自定义 Blueprint 函数（K2Node_FunctionEntry + K2Node_FunctionResult）
- 函数参数和返回值定义
- 纯函数标记
- 自定义事件（K2Node_CustomEvent）
- Event Dispatcher（K2Node_CreateDelegate）

### 1.4 节点自动布局

实现节点位置自动计算算法，避免手动指定 node_position 时节点重叠。

### 交付物

- [ ] 7 种控制流节点
- [ ] SpawnActor + Cast 节点
- [ ] Variable Set 命令
- [ ] 数学/逻辑/比较节点（通过 CallFunction 扩展）
- [ ] 自定义函数创建
- [ ] 自定义事件 + Event Dispatcher
- [ ] 节点自动布局
- [ ] 每种新节点的集成测试

---

## Phase 2：Blueprint 类型与 UMG 扩展 (3-4 周)

**目标：** 支持 UE5 中所有常用的 Blueprint 子类型，Widget 系统可用于实际 UI 开发。

### 2.1 Blueprint 类型

| 类型 | 优先级 | 说明 |
|------|--------|------|
| Blueprint Interface | P0 | 定义接口、函数签名、让 BP 实现接口 |
| Blueprint Function Library | P0 | 静态函数库 |
| Actor Component Blueprint | P0 | 可复用组件 |
| GameMode / GameState BP | P1 | 游戏模式 |
| PlayerController BP | P1 | 玩家控制器 |

### 2.2 UMG Widget 扩展

**P0 布局容器：** HorizontalBox, VerticalBox, Overlay, SizeBox, Spacer, GridPanel

**P0 常用 Widget：** Image, ProgressBar, Slider, CheckBox, EditableText

**P1 高级 Widget：** ScrollBox, Border, ListView, TileView, ComboBox, RichTextBlock

**布局系统增强：**
- Anchor / Alignment 设置
- Slot 属性（Padding, HAlign, VAlign, Size）
- 嵌套布局容器
- Widget 动画（基础 PropertyBinding）

### 2.3 Enhanced Input

- 创建 Input Action 资产
- 创建 Input Mapping Context
- 添加 Key Mapping 到 Context
- 输入触发器和修饰器

### 交付物

- [ ] 3 种新 Blueprint 类型
- [ ] 11+ 种新 UMG Widget
- [ ] 布局系统增强
- [ ] Enhanced Input 完整支持
- [ ] 各类型的集成测试

---

## Phase 3：资产与关卡管理 (2-3 周)

**目标：** 补全编辑器级别的操作能力。

### 3.1 资产管理（新模块 AssetCommands）

- `import_asset` — 导入外部文件（FBX/OBJ/PNG/WAV）
- `find_assets` — 按路径、类型、标签搜索
- `delete_asset` — 删除资产
- `rename_asset` / `move_asset` — 重命名 / 移动
- `duplicate_asset` — 复制资产
- `get_asset_info` — 获取资产元数据

### 3.2 材质系统

- `create_material` — 创建材质
- `create_material_instance` — 创建材质实例
- `set_material_parameter` — 设置参数（Scalar/Vector/Texture）
- `assign_material` — 将材质赋给组件

### 3.3 关卡管理（新模块 LevelCommands）

- `get_current_level` — 获取当前关卡信息
- `save_level` / `save_all` — 保存
- `create_level` — 创建新关卡
- `open_level` — 打开关卡
- `get_world_settings` / `set_world_settings` — 世界设置

### 交付物

- [ ] AssetCommands 模块（6+ 命令）
- [ ] 材质系统（4 命令）
- [ ] LevelCommands 模块（5 命令）
- [ ] 集成测试

---

## Phase 4：高级 Blueprint 功能 (3-4 周)

**目标：** 覆盖专业游戏开发场景。

### 4.1 Animation Blueprint

- 创建 Animation Blueprint
- 添加 State Machine
- 添加 State
- 添加 Transition Rule
- 设置 Animation Asset

### 4.2 Level Blueprint

- 获取 Level Blueprint 引用
- 在 Level Blueprint 中添加节点
- Level Blueprint 事件绑定

### 4.3 Timeline

- 创建 Timeline 节点
- 添加 Float/Vector/Color Track
- 设置关键帧
- 设置循环/自动播放

### 4.4 高级节点

- DataTable Row 操作
- Enhanced Input Action 节点
- Component Bound Event
- Async Action（AsyncLoadAsset 等）
- Struct 操作（Make/Break）

### 4.5 批量与异步

- `batch_execute` — 批量执行多个命令（减少延迟）
- 异步命令支持（长操作 + 进度回调）
- 命令取消机制

### 交付物

- [ ] Animation Blueprint 基础支持
- [ ] Level Blueprint 支持
- [ ] Timeline 完整支持
- [ ] 高级节点
- [ ] Batch/Async 命令

---

## Phase 5：生态与长期维护 (持续)

### 5.1 文档自动化

- 从 JSON Schema 自动生成 API 文档
- 示例项目和教程
- 视频教程 / GIF 演示

### 5.2 发布流程

- 语义化版本（SemVer）
- Changelog 自动生成
- GitHub Releases
- PyPI 发布（Python 服务器）
- UE Marketplace 上架（插件）

### 5.3 社区

- Issue 模板
- PR 模板
- 贡献者指南
- Discord / Discussion 支持

### 5.4 兼容性

- 每个 UE 大版本发布后 2 周内适配
- 维护 UE 5.3 / 5.4 / 5.5 / 5.6 的配置文件
- 自动化兼容性测试矩阵

---

## 里程碑时间线

```
v0.1.0  ← 当前 (实验性)
  │
  ▼
v0.2.0  Phase 0 完成 — 基础设施重构
  │     命令注册表 / 测试框架 / 标准化
  ▼
v0.5.0  Phase 1 完成 — 节点补全
  │     覆盖 90% 蓝图场景
  ▼
v0.7.0  Phase 2 完成 — 类型与 UMG
  │     全 BP 类型 / 完整 Widget
  ▼
v0.9.0  Phase 3 完成 — 资产与关卡
  │     编辑器级操作能力
  ▼
v1.0.0  Phase 4 完成 — 高级功能
  │     Animation BP / Timeline / Batch
  ▼
v1.x    Phase 5 持续 — 生态维护
        社区 / 发布 / 兼容性
```
