-- 添加公司定位和简报字段
-- 创建时间: 2025-01-XX

-- 添加 positioning 字段（公司定位描述）
ALTER TABLE companies 
ADD COLUMN positioning TEXT COMMENT '公司定位描述' AFTER industry;

-- 添加 brief 字段（公司简要介绍/简报）
ALTER TABLE companies 
ADD COLUMN brief TEXT COMMENT '公司简要介绍/简报' AFTER positioning;

