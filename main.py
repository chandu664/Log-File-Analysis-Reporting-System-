import sys
import os
import logging
from log_parser import LogParser
from mysql_handler import MySQLHandler
from config import Config
import argparse
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log_analyzer.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class CLIManager:
    """Manages the command-line interface."""
    
    def __init__(self, db_handler):
        self.db_handler = db_handler
        self.parser = argparse.ArgumentParser(
            description="Web Server Log Analyzer & Reporting CLI"
        )
        self._setup_parser()
    
    def _setup_parser(self):
        """Setup argument parser with all commands and options."""
        subparsers = self.parser.add_subparsers(dest='command', help='Available commands')
        
        # process_logs command
        process_parser = subparsers.add_parser('process_logs', help='Parse and load logs from a file.')
        process_parser.add_argument('file_path', type=str, help='Path to the log file.')
        process_parser.add_argument('--batch_size', type=int, default=1000, help='Batch size for DB inserts.')
        
        # generate_report command
        report_parser = subparsers.add_parser('generate_report', help='Generate various analytical reports.')
        report_subparsers = report_parser.add_subparsers(dest='report_type', help='Types of reports')
        
        # top_n_ips report
        top_ips_parser = report_subparsers.add_parser('top_n_ips', help='Top N requesting IP addresses.')
        top_ips_parser.add_argument('n', type=int, default=10, help='Number of top IPs.')
        
        # status_code_distribution report
        status_code_parser = report_subparsers.add_parser('status_code_distribution', help='HTTP status code breakdown.')
        
        # hourly_traffic report
        hourly_traffic_parser = report_subparsers.add_parser('hourly_traffic', help='Traffic distribution by hour.')
        
        # top_n_pages report
        top_pages_parser = report_subparsers.add_parser('top_n_pages', help='Top N most requested URLs.')
        top_pages_parser.add_argument('n', type=int, default=10, help='Number of top pages.')
        
        # traffic_by_os report
        traffic_os_parser = report_subparsers.add_parser('traffic_by_os', help='Breakdown of traffic by operating system.')
        
        # error_logs_by_date report
        error_logs_parser = report_subparsers.add_parser('error_logs_by_date', help='List of error logs (4xx/5xx) for a specific date.')
        error_logs_parser.add_argument('date', type=str, help='Date in YYYY-MM-DD format.')
        
        # tail_logs command (bonus)
        tail_parser = subparsers.add_parser('tail_logs', help='Continuously monitors a log file for new entries.')
        tail_parser.add_argument('file_path', type=str, help='Path to the log file to monitor.')
        tail_parser.add_argument('--interval', type=int, default=5, help='Check interval in seconds.')
    
    def run(self):
        """Execute the appropriate command based on CLI arguments."""
        args = self.parser.parse_args()
        
        if args.command == 'process_logs':
            self._process_logs(args)
        elif args.command == 'generate_report':
            self._generate_report(args)
        elif args.command == 'tail_logs':
            self._tail_logs(args)
        else:
            self.parser.print_help()
    
    def _process_logs(self, args):
        """Process log files and load into database."""
        if not os.path.exists(args.file_path):
            logging.error(f"Log file not found: {args.file_path}")
            return
        
        log_parser = LogParser()
        processed_count = 0
        batch = []
        
        logging.info(f"Processing log file: {args.file_path}")
        
        try:
            with open(args.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    parsed_data = log_parser.parse_line(line.strip())
                    if parsed_data:
                        batch.append(parsed_data)
                        
                        if len(batch) >= args.batch_size:
                            self.db_handler.insert_batch_log_entries(batch)
                            processed_count += len(batch)
                            batch = []
                            logging.info(f"Processed {processed_count} lines")
                
                # Insert remaining entries
                if batch:
                    self.db_handler.insert_batch_log_entries(batch)
                    processed_count += len(batch)
                
                logging.info(f"Finished processing log file. Total lines loaded: {processed_count}")
                
        except Exception as e:
            logging.error(f"Error processing log file: {str(e)}")
    
    def _generate_report(self, args):
        """Generate the requested report."""
        try:
            if args.report_type == 'top_n_ips':
                results = self.db_handler.get_top_n_ips(args.n)
                print(f"\nTop {args.n} Requesting IP Addresses:")
                print(tabulate(results, headers=["IP Address", "Request Count"], tablefmt="grid"))
                
            elif args.report_type == 'status_code_distribution':
                results = self.db_handler.get_status_code_distribution()
                print("\nHTTP Status Code Distribution:")
                print(tabulate(results, headers=["Status Code", "Count", "Percentage"], tablefmt="grid"))
                
            elif args.report_type == 'hourly_traffic':
                results = self.db_handler.get_hourly_traffic()
                print("\nHourly Traffic Distribution:")
                print(tabulate(results, headers=["Hour", "Request Count"], tablefmt="grid"))
                
            elif args.report_type == 'top_n_pages':
                results = self.db_handler.get_top_n_pages(args.n)
                print(f"\nTop {args.n} Most Requested URLs:")
                print(tabulate(results, headers=["URL Path", "Request Count"], tablefmt="grid"))
                
            elif args.report_type == 'traffic_by_os':
                results = self.db_handler.get_traffic_by_os()
                print("\nTraffic by Operating System:")
                print(tabulate(results, headers=["Operating System", "Request Count"], tablefmt="grid"))
                
            elif args.report_type == 'error_logs_by_date':
                results = self.db_handler.get_error_logs_by_date(args.date)
                print(f"\nError Logs for {args.date}:")
                print(tabulate(results, headers=["IP Address", "Timestamp", "Path", "Status Code", "User Agent"], tablefmt="grid"))
                
            else:
                print("Unknown report type. Use --help for available options.")
                
        except Exception as e:
            logging.error(f"Error generating report: {str(e)}")
    
    def _tail_logs(self, args):
        """Monitor log file for new entries (bonus feature)."""
        import time
        
        if not os.path.exists(args.file_path):
            logging.error(f"Log file not found: {args.file_path}")
            return
        
        log_parser = LogParser()
        
        # Get initial file size
        with open(args.file_path, 'r') as f:
            f.seek(0, 2)  # Go to end of file
            last_position = f.tell()
        
        logging.info(f"Monitoring log file: {args.file_path}")
        logging.info("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                with open(args.file_path, 'r') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    
                    if new_lines:
                        batch = []
                        for line in new_lines:
                            parsed_data = log_parser.parse_line(line.strip())
                            if parsed_data:
                                batch.append(parsed_data)
                        
                        if batch:
                            self.db_handler.insert_batch_log_entries(batch)
                            logging.info(f"Processed {len(batch)} new log entries")
                    
                    last_position = f.tell()
                
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")


def main():
    """Main application entry point."""
    try:
        # Load configuration
        config = Config()
        db_config = config.get_database_config()
        
        # Initialize database handler
        db_handler = MySQLHandler(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        
        # Create tables if they don't exist
        db_handler.create_tables()
        
        # Initialize and run CLI
        cli_manager = CLIManager(db_handler)
        cli_manager.run()
        
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        sys.exit(1)
    finally:
        try:
            db_handler.close()
        except:
            pass


if __name__ == "__main__":
    main()