-- Log File Analysis & Reporting System
-- Database Schema Creation Script

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS weblogs_db
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;

USE weblogs_db;

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS log_entries;
DROP TABLE IF EXISTS user_agents;

-- Create user_agents table
-- This table stores unique user agent strings and their parsed components
CREATE TABLE user_agents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_agent_string VARCHAR(512) UNIQUE NOT NULL,
    os VARCHAR(100) NULL COMMENT 'Operating System (Windows, macOS, Linux, etc.)',
    browser VARCHAR(100) NULL COMMENT 'Browser (Chrome, Firefox, Safari, etc.)',
    device_type VARCHAR(50) NULL COMMENT 'Device type (Desktop, Mobile, Tablet)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_user_agent_string (user_agent_string),
    INDEX idx_os (os),
    INDEX idx_browser (browser),
    INDEX idx_device_type (device_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create log_entries table
-- This table stores the main log entry data
CREATE TABLE log_entries (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ip_address VARCHAR(45) NOT NULL COMMENT 'Client IP address (IPv4/IPv6)',
    timestamp DATETIME NOT NULL COMMENT 'Exact time of the request',
    method VARCHAR(10) NOT NULL COMMENT 'HTTP method (GET, POST, etc.)',
    path VARCHAR(2048) NOT NULL COMMENT 'Requested URL path',
    status_code SMALLINT NOT NULL COMMENT 'HTTP response status code',
    bytes_sent INT NOT NULL COMMENT 'Bytes sent to client (0 for missing)',
    referrer VARCHAR(2048) NULL COMMENT 'Referrer URL',
    user_agent_id INT NULL COMMENT 'Foreign key to user_agents table',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When record was loaded',
    log_hash VARCHAR(64) UNIQUE NOT NULL COMMENT 'Unique hash for idempotency',
    
    -- Foreign key constraint
    FOREIGN KEY (user_agent_id) REFERENCES user_agents(id) ON DELETE SET NULL,
    
    -- Indexes for common query patterns
    INDEX idx_timestamp (timestamp),
    INDEX idx_ip_address (ip_address),
    INDEX idx_status_code (status_code),
    INDEX idx_method (method),
    INDEX idx_path (path(255)),
    INDEX idx_log_hash (log_hash),
    INDEX idx_created_at (created_at),
    
    -- Composite indexes for common query combinations
    INDEX idx_timestamp_status (timestamp, status_code),
    INDEX idx_ip_timestamp (ip_address, timestamp),
    INDEX idx_status_timestamp (status_code, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create a view for easy reporting queries
CREATE VIEW log_entries_with_user_agents AS
SELECT 
    le.id,
    le.ip_address,
    le.timestamp,
    le.method,
    le.path,
    le.status_code,
    le.bytes_sent,
    le.referrer,
    le.created_at,
    ua.user_agent_string,
    ua.os,
    ua.browser,
    ua.device_type
FROM log_entries le
LEFT JOIN user_agents ua ON le.user_agent_id = ua.id;

-- Create indexes on the view (if supported by MySQL version)
-- Note: These are automatically created based on the underlying table indexes

-- Sample stored procedures for common queries

-- Procedure to get top N IP addresses
DELIMITER //
CREATE PROCEDURE GetTopIPs(IN n INT)
BEGIN
    SELECT 
        ip_address, 
        COUNT(*) AS request_count
    FROM log_entries
    GROUP BY ip_address
    ORDER BY request_count DESC
    LIMIT n;
END //
DELIMITER ;

-- Procedure to get status code distribution
DELIMITER //
CREATE PROCEDURE GetStatusCodeDistribution()
BEGIN
    SELECT 
        status_code,
        COUNT(*) AS count,
        ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM log_entries)), 2) AS percentage
    FROM log_entries
    GROUP BY status_code
    ORDER BY count DESC;
END //
DELIMITER ;

-- Procedure to get hourly traffic
DELIMITER //
CREATE PROCEDURE GetHourlyTraffic()
BEGIN
    SELECT 
        DATE_FORMAT(timestamp, '%H:00') AS hour_of_day,
        COUNT(*) AS request_count
    FROM log_entries
    GROUP BY hour_of_day
    ORDER BY hour_of_day ASC;
END //
DELIMITER ;

-- Procedure to get traffic by OS
DELIMITER //
CREATE PROCEDURE GetTrafficByOS()
BEGIN
    SELECT 
        COALESCE(ua.os, 'Unknown OS') AS os,
        COUNT(le.id) AS request_count
    FROM log_entries le
    LEFT JOIN user_agents ua ON le.user_agent_id = ua.id
    GROUP BY ua.os
    ORDER BY request_count DESC;
END //
DELIMITER ;

-- Procedure to clean up old data
DELIMITER //
CREATE PROCEDURE CleanupOldData(IN days_to_keep INT)
BEGIN
    DECLARE deleted_count INT DEFAULT 0;
    
    -- Delete old log entries
    DELETE FROM log_entries 
    WHERE timestamp < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);
    
    SET deleted_count = ROW_COUNT();
    
    -- Clean up orphaned user agents
    DELETE ua FROM user_agents ua
    LEFT JOIN log_entries le ON ua.id = le.user_agent_id
    WHERE le.user_agent_id IS NULL;
    
    SELECT deleted_count AS deleted_log_entries, ROW_COUNT() AS deleted_user_agents;
END //
DELIMITER ;

-- Create a function to calculate response time percentile (if needed)
DELIMITER //
CREATE FUNCTION GetStatusCategory(status_code INT) RETURNS VARCHAR(20)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE category VARCHAR(20);
    
    CASE 
        WHEN status_code < 200 THEN SET category = 'Informational';
        WHEN status_code < 300 THEN SET category = 'Success';
        WHEN status_code < 400 THEN SET category = 'Redirection';
        WHEN status_code < 500 THEN SET category = 'Client Error';
        WHEN status_code < 600 THEN SET category = 'Server Error';
        ELSE SET category = 'Unknown';
    END CASE;
    
    RETURN category;
END //
DELIMITER ;

-- Create triggers for data validation (optional)
DELIMITER //
CREATE TRIGGER validate_log_entry_insert
BEFORE INSERT ON log_entries
FOR EACH ROW
BEGIN
    -- Validate IP address format (basic check)
    IF NEW.ip_address NOT REGEXP '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$' 
       AND NEW.ip_address NOT REGEXP '^[0-9a-fA-F:]+$' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid IP address format';
    END IF;
    
    -- Validate status code range
    IF NEW.status_code < 100 OR NEW.status_code > 599 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid HTTP status code';
    END IF;
    
    -- Validate bytes_sent is not negative
    IF NEW.bytes_sent < 0 THEN
        SET NEW.bytes_sent = 0;
    END IF;
    
    -- Truncate path if too long
    IF LENGTH(NEW.path) > 2048 THEN
        SET NEW.path = LEFT(NEW.path, 2048);
    END IF;
END //
DELIMITER ;

-- Show table information
DESCRIBE user_agents;
DESCRIBE log_entries;

-- Show indexes
SHOW INDEX FROM user_agents;
SHOW INDEX FROM log_entries;

-- Display storage engine and charset information
SELECT 
    TABLE_NAME,
    ENGINE,
    TABLE_COLLATION,
    TABLE_ROWS,
    DATA_LENGTH,
    INDEX_LENGTH
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'weblogs_db';

SHOW CREATE TABLE user_agents;
SHOW CREATE TABLE log_entries;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON weblogs_db.* TO 'loganalyzer'@'localhost';
-- GRANT EXECUTE ON weblogs_db.* TO 'loganalyzer'@'localhost';

--