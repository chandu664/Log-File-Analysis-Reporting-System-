import re
import logging
from datetime import datetime
from typing import Dict, Optional


class LogParser:
    """Parses individual log lines using regex."""
    
    # Apache Common Log Format regex pattern
    # Format: IP - - [timestamp] "method path protocol" status bytes "referrer" "user_agent"
    LOG_PATTERN = re.compile(
        r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - - \[(.*?)\] "(.*?)" (\d{3}) (\d+|-) "(.*?)" "(.*?)"'
    )
    
    def __init__(self):
        """Initialize the log parser."""
        self.parsed_count = 0
        self.error_count = 0
    
    def parse_line(self, log_line: str) -> Optional[Dict]:
        """
        Extracts structured data from a single log line.
        
        Args:
            log_line (str): Raw log line from the file
            
        Returns:
            Dict: Parsed log data or None if line is malformed
        """
        if not log_line or log_line.strip() == '':
            return None
            
        try:
            match = self.LOG_PATTERN.match(log_line.strip())
            if not match:
                logging.warning(f"Malformed log line: {log_line.strip()}")
                self.error_count += 1
                return None
            
            # Extract matched groups
            ip_address = match.group(1)
            timestamp_str = match.group(2)
            request = match.group(3)
            status_code = int(match.group(4))
            bytes_sent = match.group(5)
            referrer = match.group(6)
            user_agent = match.group(7)
            
            # Parse bytes_sent (handle '-' for missing values)
            if bytes_sent == '-':
                bytes_sent = 0
            else:
                bytes_sent = int(bytes_sent)
            
            # Parse referrer (handle '-' for missing values)
            if referrer == '-':
                referrer = None
            
            # Parse user_agent (handle '-' for missing values)
            if user_agent == '-':
                user_agent = None
            
            # Parse request string to extract method and path
            method, path = self._parse_request(request)
            
            # Parse timestamp
            timestamp = self._parse_timestamp(timestamp_str)
            if timestamp is None:
                logging.warning(f"Invalid timestamp in log line: {log_line.strip()}")
                self.error_count += 1
                return None
            
            self.parsed_count += 1
            
            return {
                'ip_address': ip_address,
                'timestamp': timestamp,
                'method': method,
                'path': path,
                'status_code': status_code,
                'bytes_sent': bytes_sent,
                'referrer': referrer,
                'user_agent': user_agent
            }
            
        except Exception as e:
            logging.warning(f"Error parsing log line: {log_line.strip()} - Error: {str(e)}")
            self.error_count += 1
            return None
    
    def _parse_request(self, request: str) -> tuple:
        """
        Parse the request string to extract HTTP method and path.
        
        Args:
            request (str): Request string like "GET /index.html HTTP/1.1"
            
        Returns:
            tuple: (method, path)
        """
        try:
            request_parts = request.split()
            if len(request_parts) >= 2:
                method = request_parts[0]
                path = request_parts[1]
            elif len(request_parts) == 1:
                method = request_parts[0]
                path = '/'
            else:
                method = 'UNKNOWN'
                path = '/'
            
            return method, path
            
        except Exception:
            return 'UNKNOWN', '/'
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """
        Parse timestamp string to datetime object.
        
        Args:
            timestamp_str (str): Timestamp string like "10/Oct/2000:13:55:36 -0700"
            
        Returns:
            datetime: Parsed datetime object or None if parsing fails
        """
        try:
            # Handle different timestamp formats
            formats = [
                '%d/%b/%Y:%H:%M:%S %z',  # With timezone
                '%d/%b/%Y:%H:%M:%S',     # Without timezone
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
            
            # If no format matches, try manual parsing
            # Split timestamp and timezone
            if ' ' in timestamp_str:
                date_part, tz_part = timestamp_str.rsplit(' ', 1)
                try:
                    dt = datetime.strptime(date_part, '%d/%b/%Y:%H:%M:%S')
                    return dt
                except ValueError:
                    pass
            
            return None
            
        except Exception as e:
            logging.debug(f"Timestamp parsing error: {str(e)}")
            return None
    
    def get_stats(self) -> Dict:
        """
        Get parsing statistics.
        
        Returns:
            Dict: Statistics about parsed and error lines
        """
        return {
            'parsed_count': self.parsed_count,
            'error_count': self.error_count,
            'total_processed': self.parsed_count + self.error_count
        }
    
    def reset_stats(self):
        """Reset parsing statistics."""
        self.parsed_count = 0
        self.error_count = 0


# Test function for the parser
def test_parser():
    """Test the log parser with sample data."""
    parser = LogParser()
    
    # Sample log lines
    test_lines = [
        '127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"',
        '192.168.1.1 - - [10/Oct/2000:13:55:37 -0700] "POST /login HTTP/1.1" 302 - "http://www.example.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
        '203.0.113.1 - - [10/Oct/2000:13:55:38 -0700] "GET /nonexistent HTTP/1.1" 404 1234 "-" "Mozilla/5.0 (Linux; Android 10; SM-G973F)"',
        'malformed log line without proper format',
        '10.0.0.1 - - [invalid-timestamp] "GET / HTTP/1.1" 200 1234 "-" "-"'
    ]
    
    print("Testing Log Parser:")
    print("-" * 50)
    
    for i, line in enumerate(test_lines, 1):
        print(f"\nTest {i}: {line[:50]}...")
        result = parser.parse_line(line)
        if result:
            print(f"Parsed successfully: {result['method']} {result['path']} -> {result['status_code']}")
        else:
            print("Failed to parse")
    
    stats = parser.get_stats()
    print(f"\nParsing Statistics:")
    print(f"Successfully parsed: {stats['parsed_count']}")
    print(f"Parsing errors: {stats['error_count']}")
    print(f"Total processed: {stats['total_processed']}")


if __name__ == "__main__":
    test_parser()