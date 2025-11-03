-- FindKP 板块数据库表结构
-- 创建时间: 2025-11-03

-- 删除已存在的表(按依赖顺序)
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS companies;

-- 公司表(重新设计)
CREATE TABLE companies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL COMMENT '公司名称',
    domain VARCHAR(255) COMMENT '公司域名',
    industry VARCHAR(100) COMMENT '行业',
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '处理状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_name (name),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公司信息表';

-- 联系人表(重新设计,支持多个联系人)
CREATE TABLE contacts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL COMMENT '关联公司ID',
    full_name VARCHAR(255) COMMENT '联系人全名',
    email VARCHAR(255) NOT NULL COMMENT '邮箱(允许重复,一人多邮箱)',
    role VARCHAR(255) COMMENT '职位',
    department VARCHAR(100) COMMENT '部门(采购/销售)',
    linkedin_url VARCHAR(512) COMMENT 'LinkedIn URL',
    twitter_url VARCHAR(512) COMMENT 'Twitter/X URL',
    phone VARCHAR(50) COMMENT '电话',
    source VARCHAR(1024) COMMENT '信息来源',
    confidence_score DECIMAL(3,2) COMMENT '置信度(0-1)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    INDEX idx_company (company_id),
    INDEX idx_email (email),
    INDEX idx_department (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='联系人信息表';

