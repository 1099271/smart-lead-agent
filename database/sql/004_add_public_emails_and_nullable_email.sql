-- 添加 public_emails 字段到 companies 表，并修改 contacts.email 为可空
-- 创建时间: 2025-01-XX

-- 添加 public_emails 字段（JSON 格式存储公共邮箱列表）
ALTER TABLE companies 
ADD COLUMN public_emails JSON COMMENT '公共邮箱列表（JSON数组格式）' AFTER brief;

-- 修改 contacts 表的 email 字段为可空
ALTER TABLE contacts 
MODIFY COLUMN email VARCHAR(255) NULL COMMENT '邮箱(允许为空)';
