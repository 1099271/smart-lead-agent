-- MySQL dump 10.13  Distrib 5.7.24, for Linux (x86_64)
--
-- Host: localhost    Database: smart_lead_dev
-- ------------------------------------------------------
-- Server version	8.0.41-0ubuntu0.24.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `companies`
--

DROP TABLE IF EXISTS `companies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `companies` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `local_name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '公司本地名称',
  `domain` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `country` varchar(100) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Vietnam' COMMENT '公司所在国家（用于本地化）',
  `industry` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `positioning` text COLLATE utf8mb4_general_ci COMMENT '公司定位描述',
  `brief` text COLLATE utf8mb4_general_ci COMMENT '公司简要介绍/简报',
  `public_emails` json DEFAULT NULL COMMENT '公共邮箱列表（JSON数组格式）',
  `status` enum('pending','processing','completed','failed','ignore') COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT (now()),
  `updated_at` timestamp NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_companies_name` (`name`),
  KEY `ix_companies_id` (`id`),
  KEY `idx_country` (`country`)
) ENGINE=InnoDB AUTO_INCREMENT=148 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `contacts`
--

DROP TABLE IF EXISTS `contacts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `contacts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `company_id` int NOT NULL,
  `full_name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮箱(允许为空)',
  `role` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `department` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `linkedin_url` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `twitter_url` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `phone` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `source` varchar(1024) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `confidence_score` decimal(3,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT (now()),
  `updated_at` timestamp NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `company_id` (`company_id`),
  KEY `ix_contacts_email` (`email`),
  KEY `ix_contacts_id` (`id`),
  KEY `ix_contacts_department` (`department`),
  CONSTRAINT `contacts_ibfk_1` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=389 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `email_tracking`
--

DROP TABLE IF EXISTS `email_tracking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `email_tracking` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email_id` int NOT NULL COMMENT '关联邮件ID',
  `event_type` enum('opened','clicked','replied') NOT NULL COMMENT '事件类型',
  `ip_address` varchar(45) DEFAULT NULL COMMENT 'IP地址（IPv4或IPv6）',
  `user_agent` varchar(512) DEFAULT NULL COMMENT '浏览器User-Agent',
  `referer` varchar(512) DEFAULT NULL COMMENT '来源页面',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '事件时间',
  PRIMARY KEY (`id`),
  KEY `idx_email_id` (`email_id`),
  KEY `idx_event_type` (`event_type`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `email_tracking_ibfk_1` FOREIGN KEY (`email_id`) REFERENCES `emails` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='邮件追踪事件表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `emails`
--

DROP TABLE IF EXISTS `emails`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `emails` (
  `id` int NOT NULL AUTO_INCREMENT,
  `contact_id` int DEFAULT NULL COMMENT '关联联系人ID',
  `company_id` int DEFAULT NULL COMMENT '关联公司ID',
  `subject` varchar(512) NOT NULL COMMENT '邮件主题',
  `html_content` text NOT NULL COMMENT 'HTML内容（已嵌入追踪像素）',
  `text_content` text COMMENT '纯文本内容（可选）',
  `to_email` varchar(255) NOT NULL COMMENT '收件人邮箱',
  `to_name` varchar(255) DEFAULT NULL COMMENT '收件人姓名',
  `from_email` varchar(255) NOT NULL COMMENT '发件人邮箱',
  `from_name` varchar(255) DEFAULT NULL COMMENT '发件人姓名',
  `tracking_id` varchar(64) NOT NULL COMMENT '唯一追踪ID',
  `tracking_pixel_url` varchar(512) DEFAULT NULL COMMENT '追踪像素URL',
  `status` enum('pending','sending','sent','failed','bounced') DEFAULT 'pending' COMMENT '邮件状态',
  `gmail_message_id` varchar(255) DEFAULT NULL COMMENT 'Gmail API返回的消息ID',
  `error_message` text COMMENT '错误信息（如果发送失败）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `sent_at` timestamp NULL DEFAULT NULL COMMENT '实际发送时间',
  `first_opened_at` timestamp NULL DEFAULT NULL COMMENT '首次打开时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `tracking_id` (`tracking_id`),
  UNIQUE KEY `gmail_message_id` (`gmail_message_id`),
  KEY `idx_to_email` (`to_email`),
  KEY `idx_status` (`status`),
  KEY `idx_tracking_id` (`tracking_id`),
  KEY `idx_gmail_message_id` (`gmail_message_id`),
  KEY `idx_contact_id` (`contact_id`),
  KEY `idx_company_id` (`company_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_sent_at` (`sent_at`),
  CONSTRAINT `emails_ibfk_1` FOREIGN KEY (`contact_id`) REFERENCES `contacts` (`id`) ON DELETE SET NULL,
  CONSTRAINT `emails_ibfk_2` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='邮件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `oauth2_callbacks`
--

DROP TABLE IF EXISTS `oauth2_callbacks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `oauth2_callbacks` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `state` varchar(255) NOT NULL COMMENT 'OAuth 2.0 state 参数（唯一标识一次授权流程）',
  `code` varchar(512) DEFAULT NULL COMMENT '授权码',
  `error` text COMMENT '错误信息',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `consumed_at` timestamp NULL DEFAULT NULL COMMENT '消费时间（标记是否已被读取）',
  `expires_at` timestamp NOT NULL COMMENT '过期时间（用于自动清理）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `state` (`state`),
  KEY `idx_state` (`state`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_expires_at` (`expires_at`),
  KEY `idx_consumed_at` (`consumed_at`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='OAuth 2.0 回调记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `oauth2_tokens`
--

DROP TABLE IF EXISTS `oauth2_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `oauth2_tokens` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `provider` varchar(50) NOT NULL DEFAULT 'gmail' COMMENT 'Token 提供者标识（用于区分不同的 token，如 "gmail"）',
  `token_json` text NOT NULL COMMENT 'Token JSON 数据（完整的 Credentials.to_json() 结果）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `provider` (`provider`),
  KEY `idx_provider` (`provider`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='OAuth 2.0 Token 存储表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `processed_files`
--

DROP TABLE IF EXISTS `processed_files`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `processed_files` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `file_path` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '文件路径',
  `file_size` bigint DEFAULT NULL COMMENT '文件大小(字节)',
  `processed_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '处理时间',
  `records_count` int DEFAULT '0' COMMENT '导入的记录数',
  PRIMARY KEY (`id`),
  UNIQUE KEY `file_path` (`file_path`),
  KEY `idx_file_path` (`file_path`(255)),
  KEY `idx_processed_at` (`processed_at`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='已处理文件记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `serper_organic_results`
--

DROP TABLE IF EXISTS `serper_organic_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `serper_organic_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `trace_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '关联响应的 traceid',
  `position` int DEFAULT NULL COMMENT '结果位置',
  `title` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '标题',
  `link` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '链接',
  `snippet` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '摘要',
  `date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '日期（可选）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_trace_id` (`trace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Serper API 搜索结果表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `serper_responses`
--

DROP TABLE IF EXISTS `serper_responses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `serper_responses` (
  `trace_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'UUID traceid',
  `q` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '搜索查询',
  `type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '搜索类型 (search/image/videos)',
  `gl` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '国家代码',
  `hl` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '语言代码',
  `location` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '位置',
  `tbs` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '时间范围',
  `engine` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '搜索引擎',
  `credits` int DEFAULT NULL COMMENT '消耗的 credits',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`trace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Serper API 响应参数表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trade_records`
--

DROP TABLE IF EXISTS `trade_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `trade_records` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `trade_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '贸易ID',
  `trade_date` datetime DEFAULT NULL COMMENT '贸易日期',
  `importer` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '进口商名称',
  `importer_country_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '进口商国家代码',
  `importer_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '进口商ID',
  `importer_en` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '进口商英文名称',
  `importer_orig` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '进口商原始名称',
  `exporter` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '出口商名称',
  `exporter_country_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '出口商国家代码',
  `exporter_orig` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '出口商原始名称',
  `catalog` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目录类型(imports/exports)',
  `state_of_origin` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '原产地',
  `state_of_destination` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目的地',
  `batch_id` bigint DEFAULT NULL COMMENT '批次ID',
  `sum_of_usd` decimal(15,2) DEFAULT NULL COMMENT '美元金额',
  `gd_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '报关单号',
  `weight_unit_price` decimal(15,4) DEFAULT NULL COMMENT '重量单价',
  `source_database` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '数据库来源',
  `product_tag` json DEFAULT NULL COMMENT '产品标签(JSON数组)',
  `goods_desc` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '商品描述',
  `goods_desc_vn` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '商品描述(越南语)',
  `hs_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'HS编码',
  `country_of_origin_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '原产国代码',
  `country_of_origin` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '原产国',
  `country_of_destination` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目的国',
  `country_of_destination_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目的国代码',
  `country_of_trade` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '贸易国家',
  `qty` decimal(15,4) DEFAULT NULL COMMENT '数量',
  `qty_unit` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '数量单位',
  `qty_unit_price` decimal(15,4) DEFAULT NULL COMMENT '数量单价',
  `weight` decimal(15,4) DEFAULT NULL COMMENT '重量',
  `transport_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '运输类型',
  `payment` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '支付方式',
  `incoterm` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '贸易术语',
  `trade_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '贸易模式',
  `rep_num` int DEFAULT NULL COMMENT '代表编号',
  `primary_flag` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '主要标识',
  `source_file` varchar(512) DEFAULT NULL COMMENT '来源文件路径',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_trade_id` (`trade_id`),
  KEY `idx_trade_date` (`trade_date`),
  KEY `idx_importer` (`importer`(255)),
  KEY `idx_exporter` (`exporter`(255)),
  KEY `idx_importer_country` (`importer_country_code`),
  KEY `idx_exporter_country` (`exporter_country_code`),
  KEY `idx_catalog` (`catalog`),
  KEY `idx_batch_id` (`batch_id`),
  KEY `idx_source_file` (`source_file`(255)),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=501 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='贸易记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-14  9:00:45
