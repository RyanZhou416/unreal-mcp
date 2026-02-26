# Blueprint 功能覆盖清单

本文档列出 UE5 蓝图系统的所有主要功能点，标记当前实现状态和计划阶段。

**图例：**
- ✅ 已实现
- 🔲 计划中 (标注目标 Phase)
- ❌ 不计划支持 (说明原因)

---

## 1. Blueprint 类型

| 类型 | 状态 | Phase | 说明 |
|------|------|-------|------|
| Actor Blueprint | ✅ | — | 创建、编译、生成 Actor 实例 |
| Widget Blueprint (UMG) | ✅ | — | 基础支持（TextBlock、Button） |
| Blueprint Interface | 🔲 | 2 | 定义接口函数签名 |
| Blueprint Function Library | 🔲 | 2 | 静态函数库 |
| Actor Component Blueprint | 🔲 | 2 | 可复用组件逻辑 |
| Animation Blueprint | 🔲 | 4 | State Machine / BlendSpace |
| Level Blueprint | 🔲 | 4 | 关卡级事件 |
| GameMode Blueprint | 🔲 | 2 | 通过 create_blueprint parent_class 支持 |
| PlayerController Blueprint | 🔲 | 2 | 同上 |
| GameState Blueprint | 🔲 | 2 | 同上 |
| Niagara System | 🔲 | 4+ | 粒子系统 |
| Material Blueprint | 🔲 | 3 | 材质节点图 |
| PCG Graph | ❌ | — | 过于专业化，优先级极低 |

---

## 2. Blueprint 节点 — K2Node 类型

### 2.1 事件节点

| 节点 | 状态 | Phase | K2Node 类型 |
|------|------|-------|------------|
| BeginPlay | ✅ | — | `K2Node_Event` |
| Tick | ✅ | — | `K2Node_Event` |
| EndPlay | ✅ | — | `K2Node_Event` |
| ActorBeginOverlap | ✅ | — | `K2Node_Event` |
| ActorEndOverlap | ✅ | — | `K2Node_Event` |
| Custom Event | 🔲 | 1 | `K2Node_CustomEvent` |
| Event Dispatcher | 🔲 | 1 | `K2Node_CreateDelegate` |
| Input Action (Legacy) | ✅ | — | `K2Node_InputAction` |
| Input Action (Enhanced) | 🔲 | 2 | `K2Node_EnhancedInputAction` |
| Input Key | 🔲 | 1 | `K2Node_InputKey` |
| Input Axis | 🔲 | 1 | `K2Node_InputAxis` |
| Input Touch | 🔲 | 2 | `K2Node_InputTouch` |
| Component Begin/End Overlap | 🔲 | 2 | `K2Node_ComponentBoundEvent` |
| On Construction | 🔲 | 2 | `K2Node_Event` |
| Any Damage | 🔲 | 2 | `K2Node_Event` |

### 2.2 控制流节点

| 节点 | 状态 | Phase | K2Node 类型 / 方式 |
|------|------|-------|-------------------|
| Branch (If) | ✅ | — | `K2Node_IfThenElse` |
| Sequence | 🔲 | 1 | MacroInstance |
| ForEachLoop | 🔲 | 1 | MacroInstance |
| ForEachLoopWithBreak | 🔲 | 1 | MacroInstance |
| WhileLoop | 🔲 | 1 | MacroInstance |
| DoOnce | 🔲 | 1 | MacroInstance |
| DoN | 🔲 | 1 | MacroInstance |
| FlipFlop | 🔲 | 1 | MacroInstance |
| Gate | 🔲 | 1 | MacroInstance |
| Delay | 🔲 | 1 | `K2Node_CallFunction` (Delay) |
| Retriggerable Delay | 🔲 | 1 | CallFunction |
| Select | 🔲 | 1 | `K2Node_Select` |
| Switch on Int | 🔲 | 1 | `K2Node_SwitchInteger` |
| Switch on String | 🔲 | 1 | `K2Node_SwitchString` |
| Switch on Enum | 🔲 | 1 | `K2Node_SwitchEnum` |

### 2.3 函数调用节点

| 节点 | 状态 | Phase | 说明 |
|------|------|-------|------|
| Call Function | ✅ | — | 通用函数调用 |
| PrintString | 🔲 | 1 | 通过 CallFunction 调用 KismetSystemLibrary |
| SpawnActor | ✅ | — | `K2Node_SpawnActorFromClass` |
| DestroyActor | 🔲 | 1 | CallFunction |
| GetAllActorsOfClass | 🔲 | 1 | CallFunction |
| SetTimer | 🔲 | 1 | CallFunction (SetTimerByFunctionName) |
| ClearTimer | 🔲 | 1 | CallFunction |
| Cast To | 🔲 | 1 | `K2Node_DynamicCast` |
| IsValid | 🔲 | 1 | CallFunction |
| GetDisplayName | 🔲 | 2 | CallFunction |
| GetActorLocation/Rotation | 🔲 | 1 | CallFunction |
| SetActorLocation/Rotation | 🔲 | 1 | CallFunction |
| AddActorWorldOffset | 🔲 | 1 | CallFunction |
| GetWorldDeltaSeconds | 🔲 | 1 | CallFunction |

### 2.4 变量节点

| 节点 | 状态 | Phase | 说明 |
|------|------|-------|------|
| Variable Get | ✅ | — | 读取蓝图变量 |
| Variable Set | 🔲 | 1 | CommonUtils 已有，需暴露为命令 |
| Self Reference | ✅ | — | 获取 Self |
| Component Reference | ✅ | — | 获取组件引用 |
| Local Variable | 🔲 | 2 | 函数内局部变量 |
| Get Class Defaults | 🔲 | 2 | 获取类默认值 |

### 2.5 数学与逻辑节点

所有数学和逻辑节点通过 `add_blueprint_function_node` 调用对应库函数实现。

| 类别 | 节点 | 状态 | Phase | 目标函数 |
|------|------|------|-------|---------|
| 算术 | Add (+) | 🔲 | 1 | KismetMathLibrary::Add_IntInt 等 |
| 算术 | Subtract (-) | 🔲 | 1 | KismetMathLibrary::Subtract_IntInt |
| 算术 | Multiply (*) | 🔲 | 1 | KismetMathLibrary::Multiply_IntInt |
| 算术 | Divide (/) | 🔲 | 1 | KismetMathLibrary::Divide_IntInt |
| 算术 | Modulo (%) | 🔲 | 1 | KismetMathLibrary::Percent_IntInt |
| 比较 | Equal (==) | 🔲 | 1 | KismetMathLibrary::EqualEqual_IntInt |
| 比较 | Not Equal (!=) | 🔲 | 1 | KismetMathLibrary::NotEqual_IntInt |
| 比较 | Greater (>) | 🔲 | 1 | KismetMathLibrary::Greater_IntInt |
| 比较 | Less (<) | 🔲 | 1 | KismetMathLibrary::Less_IntInt |
| 逻辑 | AND | 🔲 | 1 | KismetMathLibrary::BooleanAND |
| 逻辑 | OR | 🔲 | 1 | KismetMathLibrary::BooleanOR |
| 逻辑 | NOT | 🔲 | 1 | KismetMathLibrary::Not_PreBool |
| 工具 | Clamp | 🔲 | 1 | KismetMathLibrary::Clamp |
| 工具 | Lerp | 🔲 | 1 | KismetMathLibrary::Lerp |
| 工具 | Abs | 🔲 | 1 | KismetMathLibrary::Abs |
| 工具 | RandomFloat | 🔲 | 1 | KismetMathLibrary::RandomFloat |
| 向量 | MakeVector | 🔲 | 1 | KismetMathLibrary::MakeVector |
| 向量 | BreakVector | 🔲 | 1 | KismetMathLibrary::BreakVector |
| 向量 | VectorLength | 🔲 | 1 | KismetMathLibrary::VSize |
| 向量 | Normalize | 🔲 | 1 | KismetMathLibrary::Normal |
| 旋转 | MakeRotator | 🔲 | 1 | KismetMathLibrary::MakeRotator |
| 旋转 | BreakRotator | 🔲 | 1 | KismetMathLibrary::BreakRotator |

> **关键策略**：数学/逻辑节点不需要每个都写专门的 Handler。扩展 `add_blueprint_function_node` 使其能自动解析 `UKismetMathLibrary` / `UKismetSystemLibrary` 等库的函数签名和 Pin，即可覆盖数百个节点。

### 2.6 数组操作节点

| 节点 | 状态 | Phase | 说明 |
|------|------|-------|------|
| MakeArray | 🔲 | 1 | `K2Node_MakeArray` |
| Array Add | 🔲 | 1 | CallFunction (TArray::Add) |
| Array Remove | 🔲 | 1 | CallFunction |
| Array Get (by index) | 🔲 | 1 | CallFunction |
| Array Set (by index) | 🔲 | 1 | CallFunction |
| Array Length | 🔲 | 1 | CallFunction |
| Array Contains | 🔲 | 1 | CallFunction |
| Array Find | 🔲 | 1 | CallFunction |
| Array Clear | 🔲 | 1 | CallFunction |

### 2.7 结构体节点

| 节点 | 状态 | Phase | 说明 |
|------|------|-------|------|
| Make Struct | 🔲 | 2 | `K2Node_MakeStruct` |
| Break Struct | 🔲 | 2 | `K2Node_BreakStruct` |
| Set Members in Struct | 🔲 | 2 | `K2Node_SetFieldsInStruct` |

### 2.8 高级节点

| 节点 | 状态 | Phase | 说明 |
|------|------|-------|------|
| Timeline | 🔲 | 4 | `K2Node_Timeline` — 时间轴动画 |
| Format Text | 🔲 | 1 | CallFunction |
| Get Data Table Row | 🔲 | 4 | `K2Node_GetDataTableRow` |
| Async Load Asset | 🔲 | 4 | `K2Node_AsyncAction` |
| Create Widget | 🔲 | 2 | CallFunction |
| Interface Message | 🔲 | 2 | `K2Node_Message` |

---

## 3. Blueprint 结构操作

### 3.1 组件系统

| 功能 | 状态 | Phase | 说明 |
|------|------|-------|------|
| 添加组件 | ✅ | — | SCS Node 创建 |
| 设置组件属性 | ✅ | — | 支持多种类型 |
| 设置 Static Mesh | ✅ | — | 专门命令 |
| 设置物理属性 | ✅ | — | 专门命令 |
| 组件层级（父子关系） | 🔲 | 2 | AttachToComponent |
| 删除组件 | 🔲 | 2 | 移除 SCS Node |
| 组件事件绑定 | 🔲 | 2 | ComponentBoundEvent |

**已支持的组件类型：**

| 组件 | 状态 |
|------|------|
| StaticMeshComponent | ✅ |
| BoxCollisionComponent | ✅ |
| SphereCollisionComponent | ✅ |
| CameraComponent | ✅ |
| SpringArmComponent | ✅ |
| PointLightComponent | ✅ |
| SpotLightComponent | ✅ |
| FloatingPawnMovement | ✅ |
| SceneComponent | ✅ |
| ArrowComponent | ✅ |
| SkeletalMeshComponent | 🔲 Phase 2 |
| AudioComponent | 🔲 Phase 2 |
| ParticleSystemComponent | 🔲 Phase 2 |
| WidgetComponent | 🔲 Phase 2 |
| CharacterMovementComponent | 🔲 Phase 2 |
| ProjectileMovementComponent | 🔲 Phase 2 |
| RotatingMovementComponent | 🔲 Phase 2 |
| SplineComponent | 🔲 Phase 3 |
| InstancedStaticMeshComponent | 🔲 Phase 3 |

### 3.2 变量系统

| 功能 | 状态 | Phase | 说明 |
|------|------|-------|------|
| 添加变量 (Boolean) | ✅ | — | |
| 添加变量 (Integer) | ✅ | — | |
| 添加变量 (Float) | ✅ | — | |
| 添加变量 (String) | ✅ | — | |
| 添加变量 (Vector) | ✅ | — | |
| 添加变量 (Rotator) | 🔲 | 1 | |
| 添加变量 (Object Reference) | 🔲 | 1 | |
| 添加变量 (Class Reference) | 🔲 | 1 | |
| 添加变量 (Enum) | 🔲 | 1 | |
| 添加变量 (Array) | 🔲 | 1 | |
| 添加变量 (Map) | 🔲 | 2 | |
| 添加变量 (Set) | 🔲 | 2 | |
| 添加变量 (Struct) | 🔲 | 2 | |
| 设置变量默认值 | 🔲 | 1 | |
| 设置变量 Category | 🔲 | 2 | |
| 变量 Expose on Spawn | ✅ | — | is_exposed 参数 |
| 变量 BlueprintReadOnly | 🔲 | 2 | |
| 变量 Replication | 🔲 | 3 | |

### 3.3 函数系统

| 功能 | 状态 | Phase | 说明 |
|------|------|-------|------|
| 创建自定义函数 | 🔲 | 1 | FunctionEntry + FunctionResult |
| 函数参数定义 | 🔲 | 1 | |
| 函数返回值 | 🔲 | 1 | |
| 纯函数标记 | 🔲 | 1 | |
| 函数 Category | 🔲 | 2 | |
| 函数访问修饰符 | 🔲 | 2 | Public/Protected/Private |
| 宏 (Macro) 创建 | 🔲 | 3 | |

---

## 4. UMG Widget 类型

### 4.1 当前支持

| Widget | 状态 | 说明 |
|--------|------|------|
| CanvasPanel | ✅ | 作为根容器 |
| TextBlock | ✅ | 文本显示 |
| Button | ✅ | 按钮（含文本） |

### 4.2 布局容器 (Phase 2)

| Widget | Phase | 说明 |
|--------|-------|------|
| HorizontalBox | 2 | 水平布局 |
| VerticalBox | 2 | 垂直布局 |
| Overlay | 2 | 层叠布局 |
| GridPanel | 2 | 网格布局 |
| UniformGridPanel | 2 | 均匀网格 |
| SizeBox | 2 | 尺寸约束 |
| Spacer | 2 | 间距 |
| ScrollBox | 2 | 滚动容器 |
| WidgetSwitcher | 2 | 页面切换 |
| Border | 2 | 带边框容器 |

### 4.3 交互控件 (Phase 2-3)

| Widget | Phase | 说明 |
|--------|-------|------|
| Image | 2 | 图片显示 |
| ProgressBar | 2 | 进度条 |
| Slider | 2 | 滑块 |
| CheckBox | 2 | 复选框 |
| EditableText | 2 | 可编辑文本 |
| EditableTextBox | 2 | 文本输入框 |
| ComboBox | 3 | 下拉选择 |
| SpinBox | 3 | 数值输入 |
| RichTextBlock | 3 | 富文本 |
| ListView | 3 | 列表视图 |
| TileView | 3 | 瓦片视图 |
| TreeView | 3 | 树视图 |

### 4.4 布局系统增强 (Phase 2)

| 功能 | Phase | 说明 |
|------|-------|------|
| Anchor 设置 | 2 | 锚点定位 |
| Alignment 设置 | 2 | 对齐方式 |
| Slot Padding | 2 | 内边距 |
| Slot HAlign/VAlign | 2 | 水平/垂直对齐 |
| Slot Size (Fill/Auto) | 2 | 尺寸模式 |
| ZOrder | ✅ | 已支持 |
| Widget Visibility | 2 | 可见性控制 |
| Widget IsEnabled | 2 | 启用状态 |

---

## 5. 编辑器操作

### 5.1 Actor 管理

| 功能 | 状态 | Phase |
|------|------|-------|
| 获取所有 Actor | ✅ | — |
| 按名称查找 Actor | ✅ | — |
| 创建 Actor | ✅ | — |
| 删除 Actor | ✅ | — |
| 设置 Transform | ✅ | — |
| 获取属性 | ✅ | — |
| 设置属性 | ✅ | — |
| 生成 Blueprint Actor | ✅ | — |
| 复制 Actor | 🔲 | 2 |
| 按类型查找 Actor | 🔲 | 2 |
| 选中 Actor | 🔲 | 2 |
| Actor 标签操作 | 🔲 | 2 |
| Actor 层 (Layer) 操作 | 🔲 | 3 |
| Actor 文件夹 (Folder) | 🔲 | 3 |

### 5.2 视口与编辑器

| 功能 | 状态 | Phase |
|------|------|-------|
| 聚焦视口 | 🔲 (有 bug) | 0 修复 |
| 截图 | ✅ | — |
| 获取引擎信息 | ✅ | — |
| Play In Editor | 🔲 | 3 |
| 停止 PIE | 🔲 | 3 |
| Undo / Redo | 🔲 | 2 |

### 5.3 资产管理

| 功能 | 状态 | Phase |
|------|------|-------|
| 导入资产 | 🔲 | 3 |
| 搜索资产 | 🔲 | 3 |
| 删除资产 | 🔲 | 3 |
| 重命名/移动资产 | 🔲 | 3 |
| 获取资产信息 | 🔲 | 3 |
| 创建材质 | 🔲 | 3 |
| 设置材质参数 | 🔲 | 3 |
| 创建材质实例 | 🔲 | 3 |

### 5.4 关卡管理

| 功能 | 状态 | Phase |
|------|------|-------|
| 获取当前关卡 | 🔲 | 3 |
| 保存关卡 | 🔲 | 3 |
| 加载关卡 | 🔲 | 3 |
| 创建关卡 | 🔲 | 3 |
| 世界设置 | 🔲 | 3 |

---

## 6. 覆盖率统计

| 类别 | 已实现 | 计划中 | 总计 | 覆盖率 |
|------|--------|--------|------|--------|
| Blueprint 类型 | 2 | 9 | 11 | 18% |
| K2Node 类型 | 8 | 38+ | 46+ | 17% |
| UMG Widget | 3 | 23 | 26 | 12% |
| 组件类型 | 10 | 9 | 19 | 53% |
| 变量类型 | 5 | 8 | 13 | 38% |
| 编辑器操作 | 9 | 20+ | 29+ | 31% |
| **总计** | **37** | **107+** | **144+** | **26%** |

Phase 1 完成后预计覆盖率提升至 **55%**。
Phase 2 完成后预计覆盖率提升至 **75%**。
Phase 4 完成后目标覆盖率 **90%+**。
