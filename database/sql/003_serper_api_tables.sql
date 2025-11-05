-- Serper API 请求响应记录表结构
-- 创建时间: 2025-01-03

-- 删除已存在的表(按依赖顺序)
DROP TABLE IF EXISTS serper_organic_results;
DROP TABLE IF EXISTS serper_responses;

-- Serper API 响应参数表
CREATE TABLE serper_responses (
    trace_id VARCHAR(36) PRIMARY KEY COMMENT 'UUID traceid',
    q VARCHAR(512) COMMENT '搜索查询',
    type VARCHAR(50) COMMENT '搜索类型 (search/image/videos)',
    gl VARCHAR(10) COMMENT '国家代码',
    hl VARCHAR(10) COMMENT '语言代码',
    location VARCHAR(100) COMMENT '位置',
    tbs VARCHAR(50) COMMENT '时间范围',
    engine VARCHAR(50) COMMENT '搜索引擎',
    credits INT COMMENT '消耗的 credits',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Serper API 响应参数表';

-- Serper API 搜索结果表
CREATE TABLE serper_organic_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    trace_id VARCHAR(36) NOT NULL COMMENT '关联响应的 traceid',
    position INT COMMENT '结果位置',
    title VARCHAR(512) COMMENT '标题',
    link VARCHAR(1024) COMMENT '链接',
    snippet TEXT COMMENT '摘要',
    date VARCHAR(50) COMMENT '日期（可选）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_trace_id (trace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Serper API 搜索结果表';

