## 包管理

已经手动用uv创建过环境了。
使用 `uv` 管理依赖，**禁止直接编辑 pyproject.toml**。正确方式：

```bash
uv add <package>      # 添加依赖
uv remove <package>   # 移除依赖
```
