-- Try in Mysql Workbench to get the results

# creating the database
CREATE DATABASE weblogs_db;

# use the database
USE weblogs_db;

# retrive the records of table log_entries
select * from log_entries;

# retrive the records of table user_agents
select * from user_agents;

SELECT ip_address, path, referrer, user_agent_id, 
       CASE WHEN referrer IS NULL THEN 'Direct Access' ELSE 'From Another Page' END as access_type
FROM log_entries LIMIT 5;

-- Analyze NULL patterns (this is valuable business intelligence!)
SELECT 
    COUNT(*) as total_requests,
    COUNT(referrer) as requests_with_referrer,
    COUNT(*) - COUNT(referrer) as direct_requests,
    ROUND((COUNT(*) - COUNT(referrer)) * 100.0 / COUNT(*), 2) as direct_traffic_percentage
FROM log_entries;

-- How much of our traffic is direct vs. from other sites?
SELECT 
    CASE WHEN referrer IS NULL THEN 'Direct Traffic' ELSE 'Referral Traffic' END as traffic_type,
    COUNT(*) as requests
FROM log_entries 
GROUP BY CASE WHEN referrer IS NULL THEN 'Direct Traffic' ELSE 'Referral Traffic' END;

SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    DATA_LENGTH,
    INDEX_LENGTH,
    (DATA_LENGTH + INDEX_LENGTH) AS TOTAL_SIZE
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'weblogs_db';
