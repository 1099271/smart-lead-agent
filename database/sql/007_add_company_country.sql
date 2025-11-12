-- 为公司表添加 country 字段
-- 创建时间: 2025-11-12
-- 说明: 添加 country 字段用于本地化配置，不允许为空

-- 添加 country 字段
ALTER TABLE companies
ADD COLUMN country VARCHAR(100) NOT NULL DEFAULT 'Vietnam' COMMENT '公司所在国家（用于本地化）' AFTER domain;

-- 添加索引以提高查询性能
CREATE INDEX idx_country ON companies(country);

-- 注意: 如果表中已有数据，需要手动更新 country 字段的值
-- UPDATE companies SET country = 'Vietnam' WHERE country IS NULL OR country = '';

