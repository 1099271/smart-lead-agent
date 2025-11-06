-- 已处理文件记录表结构
-- 创建时间: 2025-01-XX

-- 删除已存在的表
DROP TABLE IF EXISTS processed_files;

-- 已处理文件记录表
CREATE TABLE processed_files (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    file_path VARCHAR(512) UNIQUE NOT NULL COMMENT '文件路径',
    file_size BIGINT COMMENT '文件大小(字节)',
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '处理时间',
    records_count INT DEFAULT 0 COMMENT '导入的记录数',
    
    INDEX idx_file_path (file_path(255)),
    INDEX idx_processed_at (processed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='已处理文件记录表';

