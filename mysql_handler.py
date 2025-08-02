"""
MySQL Handler Module
Manages MySQL database connections and operations for log data
"""

import mysql.connector
from mysql.connector import Error
import logging
from typing import List, Dict, Optional, Tuple
import hashlib


class MySQLHandler:
    """Manages MySQL database connections and operations."""
    
    def __init__(self, host: str, user: str, password: str, database: str):
        """
        Initialize MySQL connection.
        
        Args:
            host (str): MySQL host
            user (str): MySQL username
            password (str): MySQL password
            database (str): Database name
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None
        self._connect()
    
    def _connect(self):
        """Establish connection to MySQL database."""
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=False,
                buffered=True
            )
            self.cursor = self.conn.cursor()
            logging.info("Successfully connected to MySQL database")
            
        except Error as e:
            logging.error(f"Error connecting to MySQL: {str(e)}")
            raise
    
    def create_tables(self):
        """Creates log_entries and user_agents tables if they don't exist."""
        try:
            # Create user_agents table
            create_user_agents_table = """
            CREATE TABLE IF NOT EXISTS user_agents (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_agent_string VARCHAR(512) UNIQUE NOT NULL,
                os VARCHAR(100) NULL,
                browser VARCHAR(100) NULL,
                device_type VARCHAR(50) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_agent_string (user_agent_string)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            # Create log_entries table
            create_log_entries_table = """
            CREATE TABLE IF NOT EXISTS log_entries (
                id INT PRIMARY KEY AUTO_INCREMENT,
                ip_address VARCHAR(45) NOT NULL,
                timestamp DATETIME NOT NULL,
                method VARCHAR(10) NOT NULL,
                path VARCHAR(2048) NOT NULL,
                status_code SMALLINT NOT NULL,
                bytes_sent INT NOT NULL,
                referrer VARCHAR(2048) NULL,
                user_agent_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                log_hash VARCHAR(64) UNIQUE NOT NULL,
                FOREIGN KEY (user_agent_id) REFERENCES user_agents(id),
                INDEX idx_timestamp (timestamp),
                INDEX idx_ip_address (ip_address),
                INDEX idx_status_code (status_code),
                INDEX idx_path (path(255)),
                INDEX idx_log_hash (log_hash)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            self.cursor.execute(create_user_agents_table)
            self.cursor.execute(create_log_entries_table)
            self.conn.commit()
            logging.info("Database tables created successfully")
            
        except Error as e:
            logging.error(f"Error creating tables: {str(e)}")
            self.conn.rollback()
            raise
    
    def _parse_user_agent(self, user_agent_string: str) -> Dict[str, str]:
        """
        Parse user agent string to extract OS, browser, and device type.
        
        Args:
            user_agent_string (str): User agent string
            
        Returns:
            Dict: Parsed user agent components
        """
        if not user_agent_string:
            return {'os': 'Unknown OS', 'browser': 'Unknown Browser', 'device_type': 'Unknown Device'}
        
        ua = user_agent_string.lower()
        
        # Determine OS
        os = 'Unknown OS'
        if 'windows' in ua:
            os = 'Windows'
        elif 'macintosh' in ua or 'mac os' in ua:
            os = 'macOS'
        elif 'linux' in ua:
            os = 'Linux'
        elif 'android' in ua:
            os = 'Android'
        elif 'iphone' in ua or 'ios' in ua:
            os = 'iOS'
        
        # Determine browser
        browser = 'Unknown Browser'
        if 'chrome' in ua and 'edg' not in ua:
            browser = 'Chrome'
        elif 'firefox' in ua:
            browser = 'Firefox'
        elif 'safari' in ua and 'chrome' not in ua:
            browser = 'Safari'
        elif 'edg' in ua:
            browser = 'Edge'
        elif 'opera' in ua:
            browser = 'Opera'
        elif 'msie' in ua or 'trident' in ua:
            browser = 'Internet Explorer'
        
        # Determine device type
        device_type = 'Desktop'
        if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
            device_type = 'Mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            device_type = 'Tablet'
        
        return {
            'os': os,
            'browser': browser,
            'device_type': device_type
        }
    
    def _get_or_create_user_agent_id(self, user_agent_string: str) -> Optional[int]:
        """
        Get existing user agent ID or create new one.
        
        Args:
            user_agent_string (str): User agent string
            
        Returns:
            int: User agent ID or None if user_agent_string is None
        """
        if not user_agent_string:
            return None
        
        try:
            # Check if user agent already exists
            self.cursor.execute(
                "SELECT id FROM user_agents WHERE user_agent_string = %s",
                (user_agent_string,)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result[0]
            
            # Parse user agent and insert new record
            parsed_ua = self._parse_user_agent(user_agent_string)
            
            self.cursor.execute(
                """INSERT INTO user_agents 
                   (user_agent_string, os, browser, device_type) 
                   VALUES (%s, %s, %s, %s)""",
                (user_agent_string, parsed_ua['os'], parsed_ua['browser'], parsed_ua['device_type'])
            )
            
            return self.cursor.lastrowid
            
        except Error as e:
            logging.error(f"Error handling user agent: {str(e)}")
            return None
    
    def _generate_log_hash(self, log_data: Dict) -> str:
        """
        Generate unique hash for log entry to prevent duplicates.
        
        Args:
            log_data (Dict): Log entry data
            
        Returns:
            str: SHA-256 hash of log entry
        """
        # Create unique string from key log data fields
        unique_string = f"{log_data['ip_address']}_{log_data['timestamp']}_{log_data['method']}_{log_data['path']}_{log_data['status_code']}"
        return hashlib.sha256(unique_string.encode()).hexdigest()
    
    def insert_log_entry(self, log_data: Dict) -> bool:
        """
        Insert a single parsed log entry.
        
        Args:
            log_data (Dict): Parsed log entry data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate hash for idempotency
            log_hash = self._generate_log_hash(log_data)
            
            # Check if log entry already exists
            self.cursor.execute("SELECT id FROM log_entries WHERE log_hash = %s", (log_hash,))
            if self.cursor.fetchone():
                return True  # Already exists, skip
            
            # Get or create user agent ID
            user_agent_id = self._get_or_create_user_agent_id(log_data.get('user_agent'))
            
            # Insert log entry
            self.cursor.execute(
                """INSERT INTO log_entries 
                   (ip_address, timestamp, method, path, status_code, bytes_sent, referrer, user_agent_id, log_hash)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    log_data['ip_address'],
                    log_data['timestamp'],
                    log_data['method'],
                    log_data['path'],
                    log_data['status_code'],
                    log_data['bytes_sent'],
                    log_data['referrer'],
                    user_agent_id,
                    log_hash
                )
            )
            
            self.conn.commit()
            return True
            
        except Error as e:
            logging.error(f"Error inserting log entry: {str(e)}")
            self.conn.rollback()
            return False
    
    def insert_batch_log_entries(self, log_data_list: List[Dict]) -> int:
        """
        Efficiently insert a batch of parsed log entries.
        
        Args:
            log_data_list (List[Dict]): List of parsed log entries
            
        Returns:
            int: Number of successfully inserted entries
        """
        if not log_data_list:
            return 0
        
        inserted_count = 0
        
        try:
            # Process user agents first
            user_agent_cache = {}
            
            for log_data in log_data_list:
                user_agent = log_data.get('user_agent')
                if user_agent and user_agent not in user_agent_cache:
                    user_agent_id = self._get_or_create_user_agent_id(user_agent)
                    user_agent_cache[user_agent] = user_agent_id
            
            # Prepare batch insert data
            batch_data = []
            existing_hashes = set()
            
            # Get existing hashes to avoid duplicates
            hashes = [self._generate_log_hash(log_data) for log_data in log_data_list]
            if hashes:
                placeholders = ','.join(['%s'] * len(hashes))
                self.cursor.execute(f"SELECT log_hash FROM log_entries WHERE log_hash IN ({placeholders})", hashes)
                existing_hashes = {row[0] for row in self.cursor.fetchall()}
            
            # Prepare data for batch insert
            for log_data in log_data_list:
                log_hash = self._generate_log_hash(log_data)
                
                if log_hash in existing_hashes:
                    continue  # Skip duplicates
                
                user_agent = log_data.get('user_agent')
                user_agent_id = user_agent_cache.get(user_agent) if user_agent else None
                
                batch_data.append((
                    log_data['ip_address'],
                    log_data['timestamp'],
                    log_data['method'],
                    log_data['path'],
                    log_data['status_code'],
                    log_data['bytes_sent'],
                    log_data['referrer'],
                    user_agent_id,
                    log_hash
                ))
            
            # Batch insert
            if batch_data:
                self.cursor.executemany(
                    """INSERT INTO log_entries 
                       (ip_address, timestamp, method, path, status_code, bytes_sent, referrer, user_agent_id, log_hash)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    batch_data
                )
                inserted_count = self.cursor.rowcount
                self.conn.commit()
            
            logging.info(f"Successfully inserted {inserted_count} log entries")
            return inserted_count
            
        except Error as e:
            logging.error(f"Error in batch insert: {str(e)}")
            self.conn.rollback()
            return 0
    
    def get_top_n_ips(self, n: int) -> List[Tuple]:
        """
        Get top N IP addresses by request count.
        
        Args:
            n (int): Number of top IPs to return
            
        Returns:
            List[Tuple]: List of (ip_address, request_count) tuples
        """
        try:
            query = """
            SELECT ip_address, COUNT(*) AS request_count
            FROM log_entries
            GROUP BY ip_address
            ORDER BY request_count DESC
            LIMIT %s
            """
            self.cursor.execute(query, (n,))
            return self.cursor.fetchall()
            
        except Error as e:
            logging.error(f"Error getting top IPs: {str(e)}")
            return []
    
    def get_status_code_distribution(self) -> List[Tuple]:
        """
        Get distribution of HTTP status codes.
        
        Returns:
            List[Tuple]: List of (status_code, count, percentage) tuples
        """
        try:
            query = """
            SELECT 
                status_code, 
                COUNT(*) AS count,
                ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM log_entries)), 2) AS percentage
            FROM log_entries
            GROUP BY status_code
            ORDER BY count DESC
            """
            self.cursor.execute(query)
            return self.cursor.fetchall()
            
        except Error as e:
            logging.error(f"Error getting status code distribution: {str(e)}")
            return []
    
    def get_hourly_traffic(self) -> List[Tuple]:
        """
        Get traffic distribution by hour of day.
        
        Returns:
            List[Tuple]: List of (hour, request_count) tuples
        """
        try:
            query = """
            SELECT 
                DATE_FORMAT(timestamp, '%H:00') AS hour_of_day, 
                COUNT(*) AS request_count
            FROM log_entries
            GROUP BY hour_of_day
            ORDER BY hour_of_day ASC
            """
            self.cursor.execute(query)
            return self.cursor.fetchall()
            
        except Error as e:
            logging.error(f"Error getting hourly traffic: {str(e)}")
            return []
    
    def get_top_n_pages(self, n: int) -> List[Tuple]:
        """
        Get top N most requested URLs.
        
        Args:
            n (int): Number of top pages to return
            
        Returns:
            List[Tuple]: List of (path, request_count) tuples
        """
        try:
            query = """
            SELECT path, COUNT(*) AS request_count
            FROM log_entries
            GROUP BY path
            ORDER BY request_count DESC
            LIMIT %s
            """
            self.cursor.execute(query, (n,))
            return self.cursor.fetchall()
            
        except Error as e:
            logging.error(f"Error getting top pages: {str(e)}")
            return []
    
    def get_traffic_by_os(self) -> List[Tuple]:
        """
        Get traffic breakdown by operating system.
        
        Returns:
            List[Tuple]: List of (os, request_count) tuples
        """
        try:
            query = """
            SELECT 
                COALESCE(ua.os, 'Unknown OS') AS os, 
                COUNT(le.id) AS request_count
            FROM log_entries le
            LEFT JOIN user_agents ua ON le.user_agent_id = ua.id
            GROUP BY ua.os
            ORDER BY request_count DESC
            """
            self.cursor.execute(query)
            return self.cursor.fetchall()
            
        except Error as e:
            logging.error(f"Error getting traffic by OS: {str(e)}")
            return []
    
    def get_error_logs_by_date(self, date: str) -> List[Tuple]:
        """
        Get error logs (4xx/5xx) for a specific date.
        
        Args:
            date (str): Date in YYYY-MM-DD format
            
        Returns:
            List[Tuple]: List of error log entries
        """
        try:
            query = """
            SELECT 
                le.ip_address, 
                le.timestamp, 
                le.path, 
                le.status_code,
                COALESCE(ua.user_agent_string, 'Unknown') AS user_agent_string
            FROM log_entries le
            LEFT JOIN user_agents ua ON le.user_agent_id = ua.id
            WHERE DATE(le.timestamp) = %s AND le.status_code >= 400
            ORDER BY le.timestamp ASC
            """
            self.cursor.execute(query, (date,))
            return self.cursor.fetchall()
            
        except Error as e:
            logging.error(f"Error getting error logs by date: {str(e)}")
            return []
    
    def get_database_stats(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dict: Database statistics
        """
        try:
            stats = {}
            
            # Get total log entries
            self.cursor.execute("SELECT COUNT(*) FROM log_entries")
            stats['total_log_entries'] = self.cursor.fetchone()[0]
            
            # Get total user agents
            self.cursor.execute("SELECT COUNT(*) FROM user_agents")
            stats['total_user_agents'] = self.cursor.fetchone()[0]
            
            # Get date range
            self.cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM log_entries")
            result = self.cursor.fetchone()
            stats['date_range'] = {
                'earliest': result[0],
                'latest': result[1]
            }
            
            # Get unique IPs
            self.cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM log_entries")
            stats['unique_ips'] = self.cursor.fetchone()[0]
            
            return stats
            
        except Error as e:
            logging.error(f"Error getting database stats: {str(e)}")
            return {}
    
    def cleanup_old_data(self, days: int) -> int:
        """
        Clean up old log data (bonus feature).
        
        Args:
            days (int): Number of days to keep
            
        Returns:
            int: Number of deleted records
        """
        try:
            query = """
            DELETE FROM log_entries 
            WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
            """
            self.cursor.execute(query, (days,))
            deleted_count = self.cursor.rowcount
            
            # Clean up orphaned user agents
            self.cursor.execute("""
                DELETE ua FROM user_agents ua
                LEFT JOIN log_entries le ON ua.id = le.user_agent_id
                WHERE le.user_agent_id IS NULL
            """)
            
            self.conn.commit()
            logging.info(f"Cleaned up {deleted_count} old log entries")
            return deleted_count
            
        except Error as e:
            logging.error(f"Error cleaning up old data: {str(e)}")
            self.conn.rollback()
            return 0
    
    def close(self):
        """Close the database connection."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            logging.info("Database connection closed")
        except Error as e:
            logging.error(f"Error closing database connection: {str(e)}")


# Test function for the MySQL handler
def test_mysql_handler():
    """Test the MySQL handler with sample data."""
    try:
        # Test connection (update with your credentials)
        handler = MySQLHandler(
            host='localhost',
            user='root',
            password='root',
            database='weblogs_db'
        )
        
        # Test table creation
        handler.create_tables()
        print("✓ Tables created successfully")
        
        # Test sample data insertion
        sample_data = {
            'ip_address': '127.0.0.1',
            'timestamp': '2023-10-10 13:55:36',
            'method': 'GET',
            'path': '/test',
            'status_code': 200,
            'bytes_sent': 1234,
            'referrer': 'http://example.com',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        success = handler.insert_log_entry(sample_data)
        if success:
            print("✓ Sample data inserted successfully")
        
        # Test reporting
        top_ips = handler.get_top_n_ips(5)
        print(f"✓ Top IPs query returned {len(top_ips)} results")
        
        stats = handler.get_database_stats()
        print(f"✓ Database stats: {stats}")
        
        handler.close()
        print("✓ Connection closed successfully")
        
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")


if __name__ == "__main__":
    test_mysql_handler()