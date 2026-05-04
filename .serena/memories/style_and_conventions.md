# 风格与约定

- Python 3.10+，PEP 8，4 空格缩进。
- 函数、变量、模块使用 `snake_case`；类使用 `PascalCase`；内部辅助方法使用 `_` 前缀。
- GUI 逻辑保留在 `app/`，核心检测/跟踪流水线在 `core/`，统计与评估在 `analysis/` / `evaluation/`。
- 复杂处理步骤可写简短 docstring，避免业务逻辑混入界面层。
- 回答用户必须使用中文。长回复使用 Markdown 标题、引用块、分割线分段；避免长表格。