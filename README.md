# Web Server Log Analyzer & Reporting System

A comprehensive Python-based tool for parsing, analyzing, and generating reports from web server access logs. This system efficiently processes Apache Common Log Format files and stores structured data in MySQL for fast querying and analysis.

## Features

- **Log Parsing**: Robust parsing of Apache Common Log Format with error handling
- **Database Storage**: Efficient MySQL storage with optimized schema and indexing
- **Batch Processing**: High-performance batch insertion for large log files
- **Comprehensive Reporting**: Multiple built-in report types for traffic analysis
- **Real-time Monitoring**: Live log file monitoring with automatic processing
- **User Agent Analysis**: Automatic parsing of browser, OS, and device information
- **Duplicate Prevention**: Hash-based idempotency to prevent duplicate entries
- **CLI Interface**: Easy-to-use command-line interface for all operations

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
## Installation & Setup

### Prerequisites

- Python 3.7 or higher
- MySQL 5.7 or higher
- Git (for cloning the repository)


### 1. Install Python Dependencies

```
pip install -r requirements.txt
```

**Required packages:**
- `mysql-connector-python==8.0.30` - MySQL database connectivity
- `tabulate==0.9.0` - Table formatting for CLI reports
- `configparser` - Configuration file management

### 2. MySQL Database Setup

#### Option A: Automatic Setup (Recommended)

The application will automatically create the database and tables on first run. 
Simply ensure MySQL is running and update the configuration file with your credentials.

#### Option B: Manual Setup

```sql
-- Connect to MySQL as root or admin user
mysql -u root -p

-- Create database
CREATE DATABASE weblogs_db;


-- Use the databse
USE weblogs_db;
```

### 3. Configuration

Copy and customize the configuration file:

```
cp config.ini.example config.ini
```

Edit `config.ini` with your database credentials:

```ini
[DATABASE]
host = localhost
user = your_mysql_user
password = your_mysql_password
database = weblogs_db
port = 3306
```

### 5. Verify Installation

```
python main.py --help
```

## Log Format

The system supports **Apache Common Log Format** and **Apache Combined Log Format**:

### Apache Common Log Format
```
127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com/" "Mozilla/5.0..."
```

### Format Components
- **IP Address**: Client IP address (IPv4/IPv6 supported)
- **Timestamp**: Request timestamp in format `[DD/MMM/YYYY:HH:MM:SS ±HHMM]`
- **HTTP Method**: GET, POST, PUT, DELETE, etc.
- **Request Path**: URL path and query parameters
- **HTTP Protocol**: Usually HTTP/1.1 or HTTP/2.0
- **Status Code**: HTTP response status (200, 404, 500, etc.)
- **Bytes Sent**: Response size in bytes (or `-` for unknown)
- **Referrer**: Referrer URL (or `-` for direct access)
- **User Agent**: Browser/client identification string

### Supported Timestamp Formats
- `10/Oct/2023:13:55:36 +0000` (with timezone)
- `10/Oct/2023:13:55:36` (without timezone)

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐         ┌──────────────────┐
│   user_agents   │         │   log_entries    │
├─────────────────┤         ├──────────────────┤
│ id (PK)         │◄────────┤ id (PK)          │
│ user_agent_string│        │ ip_address       │
│ os              │         │ timestamp        │
│ browser         │         │ method           │
│ device_type     │         │ path             │
│ created_at      │         │ status_code      │
└─────────────────┘         │ bytes_sent       │
                            │ referrer         │
                            │ user_agent_id(FK)│
                            │ log_hash         │
                            │ created_at       │
                            └──────────────────┘
```

### Table Descriptions

#### `user_agents` Table
Stores unique user agent strings and their parsed components to normalize the data and improve query performance.

| Column | Type | Description |
|--------|------|-------------|
| `id`   | INT (PK) | Auto-incrementing primary key |
| `user_agent_string` | VARCHAR(512) | Full user agent string |
| `os` | VARCHAR(100) | Parsed operating system |
| `browser` | VARCHAR(100) | Parsed browser name |
| `device_type` | VARCHAR(50) | Device category (Desktop/Mobile/Tablet) |
| `created_at` | TIMESTAMP | Record creation time |

#### `log_entries` Table
Main table storing all log entry data with optimized indexing for fast queries.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT (PK) | Auto-incrementing primary key |
| `ip_address` | VARCHAR(45) | Client IP address (IPv4/IPv6) |
| `timestamp` | DATETIME | Request timestamp |
| `method` | VARCHAR(10) | HTTP method |
| `path` | VARCHAR(2048) | Requested URL path |
| `status_code` | SMALLINT | HTTP status code |
| `bytes_sent` | INT | Response size in bytes |
| `referrer` | VARCHAR(2048) | Referrer URL (nullable) |
| `user_agent_id` | INT (FK) | Foreign key to user_agents |
| `log_hash` | VARCHAR(64) | SHA-256 hash for deduplication |
| `created_at` | TIMESTAMP | Record creation time |

### Indexes

The schema includes optimized indexes for common query patterns:

- **Primary Indexes**: `ip_address`, `timestamp`, `status_code`, `method`, `path`
- **Composite Indexes**: `(timestamp, status_code)`, `(ip_address, timestamp)`
- **Unique Constraints**: `log_hash`, `user_agent_string`

## Implementation methodology

# ELT Pipeline Implementation

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ELT PROCESS ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                     EXTRACT PHASE                              │ │
│  │                                                                 │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    │ │
│  │  │ Log Files   │───▶│File Reading │───▶│ Basic Parsing   │    │ │
│  │  │ • access.log│    │• Streaming  │    │ • Regex Match   │    │ │
│  │  │ • error.log │    │• Line-by-   │    │ • Field Extract │    │ │
│  │  │ • custom    │    │  line       │    │ • Data Types    │    │ │
│  │  └─────────────┘    └─────────────┘    └─────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                    │                                 │
│                                    ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                      LOAD PHASE                                │ │
│  │                                                                 │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    │ │
│  │  │Raw Data     │───▶│Batch Insert │───▶│  MySQL Database │    │ │
│  │  │Preparation  │    │• Bulk Ops   │    │  • log_entries  │    │ │
│  │  │• Minimal    │    │• Transaction│    │  • user_agents  │    │ │
│  │  │  Validation │    │• Performance│    │  • Raw Storage  │    │ │
│  │  └─────────────┘    └─────────────┘    └─────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                    │                                 │
│                                    ▼                                 │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   TRANSFORM PHASE                              │ │
│  │                                                                 │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    │ │
│  │  │SQL Queries  │───▶│Aggregations │───▶│ Business Logic  │    │ │
│  │  │• JOINs      │    │• GROUP BY   │    │ • Reports       │    │ │
│  │  │• CTEs       │    │• SUM/COUNT  │    │ • Analytics     │    │ │
│  │  │• Views      │    │• Window Fn  │    │ • Insights      │    │ │
│  │  └─────────────┘    └─────────────┘    └─────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## CLI Usage Guide

### Basic Commands

#### 1. Process Log Files

```
# Process a single log file
python main.py process_logs /var/log/apache2/access.log

# Process with custom batch size for large files
python main.py process_logs /var/log/apache2/access.log --batch_size 5000

# Process sample logs (for testing)
python main.py process_logs sample_logs/access.log
```

#### 2. Generate Reports

##### Top IP Addresses
```
# Top 10 requesting IPs (default)
python main.py generate_report top_n_ips 10

# Top 25 requesting IPs
python main.py generate_report top_n_ips 25
```

##### Status Code Distribution
```
python main.py generate_report status_code_distribution
```

##### Hourly Traffic Analysis
```
python main.py generate_report hourly_traffic
```

##### Most Requested Pages
```
# Top 10 pages (default)
python main.py generate_report top_n_pages 10

# Top 50 pages
python main.py generate_report top_n_pages 50
```

##### Traffic by Operating System
```
python main.py generate_report traffic_by_os
```

##### Error Logs by Date
```
# Get all 4xx/5xx errors for a specific date
python main.py generate_report error_logs_by_date 2023-10-10
```

#### 3. Real-time Log Monitoring

```
# Monitor log file for new entries (checks every 5 seconds)
python main.py tail_logs /var/log/apache2/access.log

# Custom check interval (10 seconds)
python main.py tail_logs /var/log/apache2/access.log --interval 10
```

### Example Output

#### Top IP Addresses Report
```
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

#### Status Code Distribution
```
HTTP Status Code Distribution:
+---------------+---------+--------------+
|   Status Code |   Count |   Percentage |
+===============+=========+==============+
|           200 |      34 |        66.67 |
+---------------+---------+--------------+
|           302 |       3 |         5.88 |
+---------------+---------+--------------+
|           404 |       2 |         3.92 |
+---------------+---------+--------------+
|           500 |       2 |         3.92 |
+---------------+---------+--------------+
|           101 |       1 |         1.96 |
+---------------+---------+--------------+
|           201 |       1 |         1.96 |
+---------------+---------+--------------+
|           204 |       1 |         1.96 |
+---------------+---------+--------------+
|           301 |       1 |         1.96 |
+---------------+---------+--------------+
|           401 |       1 |         1.96 |
+---------------+---------+--------------+
|           403 |       1 |         1.96 |
+---------------+---------+--------------+
|           408 |       1 |         1.96 |
+---------------+---------+--------------+
|           413 |       1 |         1.96 |
+---------------+---------+--------------+
|           429 |       1 |         1.96 |
+---------------+---------+--------------+
|           503 |       1 |         1.96 |
+---------------+---------+--------------+

```

## Configuration

### Configuration File (`config.ini`)

```ini
[DATABASE]
host = localhost
user = root
password = your_password
database = weblogs_db
port = 3306

[APPLICATION]
default_batch_size = 1000
log_level = INFO
max_file_size_mb = 100
date_format = %Y-%m-%d
datetime_format = %Y-%m-%d %H:%M:%S

[LOG_PATTERNS]
apache_common = (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - - \[(.*?)\] "(.*?)" (\d{3}) (\d+|-) "(.*?)" "(.*?)"
apache_combined = (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - - \[(.*?)\] "(.*?)" (\d{3}) (\d+|-) "(.*?)" "(.*?)"

[PERFORMANCE]
batch_size = 1000
connection_timeout = 30
query_timeout = 60
max_connections = 10

[MONITORING]
tail_interval = 5
alert_error_threshold = 100
alert_time_window = 300
```

### Environment Variables

You can override configuration using environment variables:

```
export DB_HOST=localhost
export DB_USER=loganalyzer
export DB_PASSWORD=secure_password
export DB_NAME=weblogs_db
export DB_PORT=3306
```

## Report Types

### 1. **Top N IP Addresses**
- **Purpose**: Identify high-traffic sources
- **Use Cases**: traffic analysis, user behavior
- **Output**: IP address and request count

### 2. **Status Code Distribution**
- **Purpose**: Monitor server health and error rates
- **Use Cases**: Error monitoring, performance analysis
- **Output**: Status codes with counts and percentages

### 3. **Hourly Traffic Pattern**
- **Purpose**: Understand traffic patterns throughout the day
- **Use Cases**: Capacity planning, maintenance scheduling
- **Output**: Hour-by-hour request counts

### 4. **Top Requested Pages**
- **Purpose**: Identify popular content
- **Use Cases**: Content optimization, caching strategy
- **Output**: URL paths with request counts

### 5. **Traffic by Operating System**
- **Purpose**: Understand user demographics
- **Use Cases**: Browser compatibility, mobile optimization
- **Output**: OS distribution with request counts

### 6. **Error Logs by Date**
- **Purpose**: Troubleshoot specific issues
- **Use Cases**: Debugging, incident analysis
- **Output**: Detailed error entries for specific dates

## Regex Patterns

### Apache Common Log Pattern

```regex
(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - - \[(.*?)\] "(.*?)" (\d{3}) (\d+|-) "(.*?)" "(.*?)"
```

#### Pattern Breakdown:

1. **`(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})`** - **IP Address**
   - Matches IPv4 addresses (1-3 digits per octet)
   - Example: `192.168.1.100`

2. **`\[(.*?)\]`** - **Timestamp**
   - Non-greedy match between square brackets
   - Example: `[10/Oct/2023:13:55:36 +0000]`

3. **`"(.*?)"`** - **HTTP Request**
   - Request method, path, and protocol
   - Example: `"GET /index.html HTTP/1.1"`

4. **`(\d{3})`** - **Status Code**
   - Exactly 3 digits
   - Example: `200`, `404`, `500`

5. **`(\d+|-)`** - **Bytes Sent**
   - Either digits or hyphen for missing data
   - Example: `1234` or `-`

6. **`"(.*?)"`** - **Referrer**
   - Referrer URL in quotes
   - Example: `"http://example.com/"` or `"-"`

7. **`"(.*?)"`** - **User Agent**
   - Browser/client identification
   - Example: `"Mozilla/5.0 (Windows NT 10.0; ...)"`

### Error Handling

The parser gracefully handles malformed entries:
- Invalid IP addresses
- Malformed timestamps
- Incomplete log lines
- Special characters in URLs
- Missing fields

## Performance Optimization

### Database Optimizations

1. **Indexing Strategy**
   - Primary indexes on frequently queried columns
   - Composite indexes for multi-column queries
   - Covering indexes to avoid table lookups

2. **Batch Processing**
   - Default batch size: 1000 records
   - Configurable for memory/performance tuning
   - Transaction-based commits for data integrity

3. **Data Normalization**
   - User agent strings stored separately to reduce redundancy
   - Foreign key relationships for efficient joins

### Application Optimizations

1. **Memory Management**
   - Streaming file processing for large files
   - Generator-based parsing to minimize memory usage
   - Connection pooling for database efficiency

2. **Duplicate Prevention**
   - SHA-256 hashing for idempotent operations
   - Unique constraints prevent duplicate insertions
   - Batch duplicate checking for performance

### Recommended Settings for Large Files

```ini
[PERFORMANCE]
batch_size = 5000          # Larger batches for big files
connection_timeout = 60    # Extended timeout
max_connections = 20       # More concurrent connections
```

## Known Limitations

### 1. **Log Format Support**
- **Current**: Apache Common/Combined Log Format only
- **Missing**: Nginx custom formats, JSON logs
- **Workaround**: Convert logs to supported format

### 2. **IPv6 Support**
- **Status**: Basic support implemented
- **Limitation**: IPv6 regex validation could be more robust
- **Impact**: Some IPv6 addresses might not parse correctly

### 3. **Timezone Handling**
- **Current**: Basic timezone parsing
- **Limitation**: Complex timezone conversions not supported
- **Impact**: All timestamps stored as-is from logs

### 4. **Memory Usage**
- **Large Files**: Memory usage scales with batch size
- **Recommendation**: Adjust batch size for available memory
- **Monitoring**: Watch memory usage with very large files (>10GB)

### 5. **Concurrent Processing**
- **Current**: Single-threaded processing
- **Limitation**: Cannot process multiple files simultaneously
- **Impact**: Slower processing for multiple log files

### 6. **Real-time Performance**
- **Tail Mode**: 5-second default polling interval
- **Limitation**: Not true real-time, polling-based
- **Alternative**: Consider log streaming solutions for high-volume

### 7. **User Agent Parsing**
- **Current**: Basic pattern matching
- **Limitation**: May not detect all browser/OS combinations
- **Accuracy**: ~90% accuracy for common user agents

## Future Improvements

### Planned Features

#### 1. **Enhanced Log Format Support**
- Nginx log format support
- IIS W3C Extended Log Format
- Custom log format configuration
- JSON-based log parsing

#### 2. **Advanced Analytics**
- Geographic IP analysis with GeoIP database
- Bot detection and filtering
- Anomaly detection for security monitoring
- Real-time alerting system

#### 3. **Performance Enhancements**
- Multi-threaded log processing
- Parallel file processing
- Compressed log file support (.gz, .bz2)
- Streaming analytics for real-time insights

#### 4. **Reporting & Visualization**
- Web-based dashboard
- Interactive charts and graphs
- PDF report generation
- Scheduled report delivery via email

#### 5. **Data Export & Integration**
- Export to CSV, JSON, Excel formats
- Elasticsearch integration
- Splunk connector
- REST API for external integrations

#### 6. **Advanced Features**
- Session tracking and user journey analysis
- A/B testing support
- Custom metric calculations
- Data retention policies with automatic archiving
