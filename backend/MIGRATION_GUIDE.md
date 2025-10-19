# 数据库迁移指南

## 问题
添加了新的 `user_id` 列到 `orders` 和 `licenses` 表，但现有数据库没有这些列。

## 解决方案（选择其一）

### 方案1：运行迁移脚本（推荐，保留数据）

```bash
cd /data/vibe-checker/ai_check/backend
python migrate_add_user_id.py
```

### 方案2：手动执行SQL（保留数据）

```bash
cd /data/vibe-checker/ai_check/backend
sqlite3 app.db
```

然后在 SQLite 命令行中执行：

```sql
-- 添加 user_id 列到 orders 表
ALTER TABLE orders ADD COLUMN user_id TEXT;

-- 添加 user_id 列到 licenses 表
ALTER TABLE licenses ADD COLUMN user_id TEXT;

-- 退出
.quit
```

### 方案3：删除数据库重新创建（会丢失所有数据）

⚠️ **警告**：这会删除所有现有数据！仅在测试环境使用。

```bash
cd /data/vibe-checker/ai_check/backend
rm app.db
# 重启应用，数据库会自动重新创建
```

## 验证迁移

迁移完成后，重启后端服务：

```bash
cd /data/vibe-checker/ai_check/backend
python run.py
```

检查日志应该看到 "数据库表创建/更新成功"

