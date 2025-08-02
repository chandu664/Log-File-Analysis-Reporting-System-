# Log File Analysis & Reporting System 

A comprehensive command-line application for processing web server log files, storing data in MySQL, and generating analytical reports. This project implements a complete data engineering pipeline for semi-structured operational data.

## Project Overview

This CLI tool can:
- Parse Apache Common Log Format files
- Extract and normalize log data
- Store data efficiently in MySQL database
- Generate various analytical reports
- Monitor log files in real-time (bonus feature)
- Handle large files with batch processing

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Log Files     │───▶│ Log Parser   │───▶│ MySQL Database │
│ (Apache Format) │    │ (Regex)      │    │ (Normalized)    │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                      │
                              ▼                      ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │ Data Transform   │    │ Report Generator│
                    │ & Validation     │    │ (SQL Queries)   │
                    └──────────────────┘    └─────────────────┘
```

## Requirements

### System Requirements
- Python 3.8+
- MySQL 5.7+ or MariaDB 10.2+
- At least 2GB RAM for large log files
- 10GB+ disk space for database storage

### Python Dependencies
```
pip install -r requirements.txt
```

## Installation & Setup

### 1. Clone/Download Project Files
```
# Create project directory
mkdir log_analyzer_cli
cd log_analyzer_cli

# make all project files to this directory
# - main.py
# - log_parser.py  
# - mysql_handler.py
# - config.py
# - requirements.txt
# - config.ini
# - sql/create_tables.sql
# - sample_logs/access.log
```

### 2. Install Dependencies
```
pip install -r requirements.txt
```

### 3. Setup MySQL Database
```
# Login to MySQL
mysql -u root -p

# Create database and user
mysql> source sql/create_tables.sql

# Or manually:
mysql> CREATE DATABASE weblogs_db;
mysql> USE weblogs_db;
mysql> source sql/create_tables.sql;
```

### 4. Configure Database Connection
`config.ini` with your MySQL credentials:
```ini
[DATABASE]
host = localhost
user = root
password = your_actual_password
database = weblogs_db
port = 3306
```

Or set environment variables:
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=weblogs_db
```

### 5. Test Installation
```
python main.py --help
```

## Usage Guide

### Process Log Files
```
# Basic usage
python main.py process_logs sample_logs/access.log

# With custom batch size
python main.py process_logs sample_logs/access.log --batch_size 500

# Process large files efficiently
python main.py process_logs /var/log/apache2/access.log --batch_size 2000
```

### Generate Reports

#### Top IP Addresses
```
# Top 10 IPs (default)
python main.py generate_report top_n_ips 10

# Top 5 IPs
python main.py generate_report top_n_ips 5
```

#### Status Code Distribution
```
python main.py generate_report status_code_distribution
```

#### Hourly Traffic Analysis
```
python main.py generate_report hourly_traffic
```

#### Top Requested Pages
```
python main.py generate_report top_n_pages 10
```

#### Traffic by Operating System
```
python main.py generate_report traffic_by_os
```

#### Error Logs by Date
```
python main.py generate_report error_logs_by_date 2023-10-10
```

### Real-time Log Monitoring (Bonus)
```
# Monitor log file for new entries
python main.py tail_logs /var/log/apache2/access.log --interval 5
```

## Sample Output

### Processing Logs
```
$ python main.py process_logs sample_logs/access.log
2025-08-02 16:37:21,931 - INFO - Configuration loaded from config.ini
2025-08-02 16:37:22,293 - INFO - package: mysql.connector.plugins
2025-08-02 16:37:22,294 - INFO - plugin_name: caching_sha2_password
2025-08-02 16:37:22,297 - INFO - AUTHENTICATION_PLUGIN_CLASS: MySQLCachingSHA2PasswordAuthPlugin
2025-08-02 16:37:22,346 - INFO - Successfully connected to MySQL database
2025-08-02 16:37:22,401 - INFO - Database tables created successfully
2025-08-02 16:37:22,409 - INFO - Processing log file: sample_logs/access.log
2025-08-02 16:37:22,469 - WARNING - Malformed log line: malformed log line without proper format - this should be skipped
2025-08-02 16:37:22,470 - WARNING - Invalid timestamp in log line: 127.0.0.5 - - [invalid-timestamp] "GET /test HTTP/1.1" 200 1234 "-" "-"
2025-08-02 16:37:22,471 - WARNING - Malformed log line: - incomplete log entry
2025-08-02 16:37:22,529 - INFO - Successfully inserted 0 log entries
2025-08-02 16:37:22,529 - INFO - Finished processing log file. Total lines loaded: 51
2025-08-02 16:37:22,530 - INFO - Database connection closed
```

### Top IP Addresses Report
```
$ python main.py generate_report top_n_ips 5

Top 5 Requesting IP Addresses:
+---------------+-----------------+
| IP Address    |   Request Count |
+===============+=================+
| 192.168.1.100 |               2 |
+---------------+-----------------+
| 198.51.100.1  |               2 |
+---------------+-----------------+
| 10.0.0.5      |               2 |
+---------------+-----------------+
| 172.16.0.2    |               2 |
+---------------+-----------------+
| 127.0.0.1     |               2 |
+---------------+-----------------+
```

## Database Schema

### Tables Structure

#### `log_entries` Table
| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Unique log entry ID |
| ip_address | VARCHAR(45) | Client IP address |
| timestamp | DATETIME | Request timestamp |
| method | VARCHAR(10) | HTTP method |
| path | VARCHAR(2048) | Requested URL path |
| status_code | SMALLINT | HTTP status code |
| bytes_sent | INT | Response size in bytes |
| referrer | VARCHAR(2048) | Referrer URL |
| user_agent_id | INT (FK) | Link to user_agents table |
| log_hash | VARCHAR(64) | Unique hash for deduplication |

#### `user_agents` Table
| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Unique user agent ID |
| user_agent_string | VARCHAR(512) | Full user agent string |
| os | VARCHAR(100) | Operating system |
| browser | VARCHAR(100) | Browser name |
| device_type | VARCHAR(50) | Device type |

### Indexing Strategy
- `log_entries.timestamp` - Time-based queries
- `log_entries.ip_address` - IP analysis
- `log_entries.status_code` - Error analysis
- `log_entries.path` - Page popularity
- `user_agents.user_agent_string` - Fast lookups

## Log Format Support

### Apache Common Log Format
```
IP - - [timestamp] "method path protocol" status bytes "referrer" "user_agent"
```

### Example Log Entry
```
127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

### Regex Pattern Breakdown
```python
LOG_PATTERN = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - - \[(.*?)\] "(.*?)" (\d{3}) (\d+|-) "(.*?)" "(.*?)"'
```

Groups:
1. **IP Address**: IPv4 address
2. **Timestamp**: Date and time with timezone
3. **Request**: HTTP method, path, and protocol
4. **Status Code**: HTTP response code
5. **Bytes Sent**: Response size (or '-')
6. **Referrer**: Referring URL (or '-')
7. **User Agent**: Browser/client information

## Performance Features

### Batch Processing
- Configurable batch sizes (default: 1000)
- Memory-efficient line-by-line reading
- Bulk database inserts with `executemany()`

### Data Normalization
- User agent deduplication in separate table
- Foreign key relationships for efficiency
- Indexed columns for fast