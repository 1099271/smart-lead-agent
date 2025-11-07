-- 添加公司本地名称字段
-- 创建时间: 2025-01-XX

-- 添加 local_name 字段（公司本地名称）
ALTER TABLE companies 
ADD COLUMN local_name VARCHAR(255) COMMENT '公司本地名称' AFTER name;

