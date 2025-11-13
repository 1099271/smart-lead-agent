-- OAuth 2.0 回调记录表结构
-- 创建时间: 2025-11-13
-- 用途: 存储 OAuth 2.0 授权流程中的回调信息，支持跨进程通信（CLI 和 FastAPI）

-- 删除已存在的表
DROP TABLE IF EXISTS oauth2_callbacks;

-- OAuth 2.0 回调记录表
CREATE TABLE oauth2_callbacks (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    state VARCHAR(255) UNIQUE NOT NULL COMMENT 'OAuth 2.0 state 参数（唯一标识一次授权流程）',
    code VARCHAR(512) COMMENT '授权码',
    error TEXT COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    consumed_at TIMESTAMP NULL COMMENT '消费时间（标记是否已被读取）',
    expires_at TIMESTAMP NOT NULL COMMENT '过期时间（用于自动清理）',
    
    INDEX idx_state (state),
    INDEX idx_created_at (created_at),
    INDEX idx_expires_at (expires_at),
    INDEX idx_consumed_at (consumed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OAuth 2.0 回调记录表';

