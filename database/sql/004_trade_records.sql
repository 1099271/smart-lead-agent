-- 贸易记录表结构
-- 创建时间: 2025-01-XX

-- 删除已存在的表
DROP TABLE IF EXISTS trade_records;

-- 贸易记录表
CREATE TABLE trade_records (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    trade_id VARCHAR(64) COMMENT '贸易ID',
    trade_date DATETIME COMMENT '贸易日期',
    
    -- 进口商信息
    importer VARCHAR(512) COMMENT '进口商名称',
    importer_country_code VARCHAR(10) COMMENT '进口商国家代码',
    importer_id VARCHAR(64) COMMENT '进口商ID',
    importer_en VARCHAR(512) COMMENT '进口商英文名称',
    importer_orig VARCHAR(512) COMMENT '进口商原始名称',
    
    -- 出口商信息
    exporter VARCHAR(512) COMMENT '出口商名称',
    exporter_country_code VARCHAR(10) COMMENT '出口商国家代码',
    exporter_orig VARCHAR(512) COMMENT '出口商原始名称',
    
    -- 贸易基本信息
    catalog VARCHAR(50) COMMENT '目录类型(imports/exports)',
    state_of_origin VARCHAR(100) COMMENT '原产地',
    state_of_destination VARCHAR(100) COMMENT '目的地',
    batch_id BIGINT COMMENT '批次ID',
    sum_of_usd DECIMAL(15, 2) COMMENT '美元金额',
    gd_no VARCHAR(64) COMMENT '报关单号',
    weight_unit_price DECIMAL(15, 4) COMMENT '重量单价',
    source_database VARCHAR(50) COMMENT '数据库来源',
    
    -- 产品信息
    product_tag JSON COMMENT '产品标签(JSON数组)',
    goods_desc TEXT COMMENT '商品描述',
    goods_desc_vn TEXT COMMENT '商品描述(越南语)',
    hs_code VARCHAR(20) COMMENT 'HS编码',
    
    -- 国家/地区信息
    country_of_origin_code VARCHAR(10) COMMENT '原产国代码',
    country_of_origin VARCHAR(100) COMMENT '原产国',
    country_of_destination VARCHAR(100) COMMENT '目的国',
    country_of_destination_code VARCHAR(10) COMMENT '目的国代码',
    country_of_trade VARCHAR(100) COMMENT '贸易国家',
    
    -- 数量信息
    qty DECIMAL(15, 4) COMMENT '数量',
    qty_unit VARCHAR(20) COMMENT '数量单位',
    qty_unit_price DECIMAL(15, 4) COMMENT '数量单价',
    weight DECIMAL(15, 4) COMMENT '重量',
    
    -- 贸易方式
    transport_type VARCHAR(50) COMMENT '运输类型',
    payment VARCHAR(50) COMMENT '支付方式',
    incoterm VARCHAR(20) COMMENT '贸易术语',
    trade_mode VARCHAR(255) COMMENT '贸易模式',
    
    -- 其他信息
    rep_num INT COMMENT '代表编号',
    primary_flag VARCHAR(10) COMMENT '主要标识',
    source_file VARCHAR(512) COMMENT '来源文件路径',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX idx_trade_id (trade_id),
    INDEX idx_trade_date (trade_date),
    INDEX idx_importer (importer(255)),
    INDEX idx_exporter (exporter(255)),
    INDEX idx_importer_country (importer_country_code),
    INDEX idx_exporter_country (exporter_country_code),
    INDEX idx_catalog (catalog),
    INDEX idx_batch_id (batch_id),
    INDEX idx_source_file (source_file(255)),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='贸易记录表';

