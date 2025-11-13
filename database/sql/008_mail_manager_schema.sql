-- MailManager 板块数据库表结构
-- 创建时间: 2024-11-13

-- 删除已存在的表(按依赖顺序)
DROP TABLE IF EXISTS email_tracking;
DROP TABLE IF EXISTS emails;

-- 邮件记录表
CREATE TABLE emails (
    id INT PRIMARY KEY AUTO_INCREMENT,
    -- 关联信息
    contact_id INT COMMENT '关联联系人ID',
    company_id INT COMMENT '关联公司ID',
    -- 邮件基本信息
    subject VARCHAR(512) NOT NULL COMMENT '邮件主题',
    html_content TEXT NOT NULL COMMENT 'HTML内容（已嵌入追踪像素）',
    text_content TEXT COMMENT '纯文本内容（可选）',
    -- 收件人信息
    to_email VARCHAR(255) NOT NULL COMMENT '收件人邮箱',
    to_name VARCHAR(255) COMMENT '收件人姓名',
    -- 发件人信息
    from_email VARCHAR(255) NOT NULL COMMENT '发件人邮箱',
    from_name VARCHAR(255) COMMENT '发件人姓名',
    -- 追踪信息
    tracking_id VARCHAR(64) UNIQUE NOT NULL COMMENT '唯一追踪ID',
    tracking_pixel_url VARCHAR(512) COMMENT '追踪像素URL',
    -- 状态信息
    status ENUM('pending', 'sending', 'sent', 'failed', 'bounced') DEFAULT 'pending' COMMENT '邮件状态',
    gmail_message_id VARCHAR(255) UNIQUE COMMENT 'Gmail API返回的消息ID',
    error_message TEXT COMMENT '错误信息（如果发送失败）',
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    sent_at TIMESTAMP NULL COMMENT '实际发送时间',
    first_opened_at TIMESTAMP NULL COMMENT '首次打开时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    -- 外键约束
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
    -- 索引
    INDEX idx_to_email (to_email),
    INDEX idx_status (status),
    INDEX idx_tracking_id (tracking_id),
    INDEX idx_gmail_message_id (gmail_message_id),
    INDEX idx_contact_id (contact_id),
    INDEX idx_company_id (company_id),
    INDEX idx_created_at (created_at),
    INDEX idx_sent_at (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邮件记录表';

-- 邮件追踪事件表
CREATE TABLE email_tracking (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email_id INT NOT NULL COMMENT '关联邮件ID',
    -- 事件类型
    event_type ENUM('opened', 'clicked', 'replied') NOT NULL COMMENT '事件类型',
    -- 追踪信息
    ip_address VARCHAR(45) COMMENT 'IP地址（IPv4或IPv6）',
    user_agent VARCHAR(512) COMMENT '浏览器User-Agent',
    referer VARCHAR(512) COMMENT '来源页面',
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '事件时间',
    -- 外键约束
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
    -- 索引
    INDEX idx_email_id (email_id),
    INDEX idx_event_type (event_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邮件追踪事件表';

