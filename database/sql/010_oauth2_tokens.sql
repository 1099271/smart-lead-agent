-- OAuth 2.0 Token 存储表结构
-- 创建时间: 2025-11-13
-- 用途: 存储 Gmail OAuth 2.0 授权后的 token 信息（JSON 格式），支持跨进程共享 token

-- 删除已存在的表
DROP TABLE IF EXISTS oauth2_tokens;

-- OAuth 2.0 Token 存储表
CREATE TABLE oauth2_tokens (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    provider VARCHAR(50) UNIQUE NOT NULL DEFAULT 'gmail' COMMENT 'Token 提供者标识（用于区分不同的 token，如 "gmail"）',
    token_json TEXT NOT NULL COMMENT 'Token JSON 数据（完整的 Credentials.to_json() 结果）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_provider (provider),
    INDEX idx_created_at (created_at),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OAuth 2.0 Token 存储表';

