-- 数据库迁移 SQL 脚本
-- 添加 user_id 列到 orders 和 licenses 表

-- 1. 添加 user_id 到 orders 表
ALTER TABLE orders ADD COLUMN user_id TEXT;

-- 2. 添加 user_id 到 licenses 表  
ALTER TABLE licenses ADD COLUMN user_id TEXT;

-- 验证
SELECT sql FROM sqlite_master WHERE name = 'orders';
SELECT sql FROM sqlite_master WHERE name = 'licenses';

