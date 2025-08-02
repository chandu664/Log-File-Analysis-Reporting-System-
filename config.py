"""
Configuration Management Module
Handles database credentials and application settings
"""

import os
import configparser
from pathlib import Path
import logging


class Config:
    """Manages application configuration."""
    
    def __init__(self, config_file='config.ini'):
        """
        Initialize configuration.
        
        Args:
            config_file (str): Path to configuration file
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file or create default."""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            logging.info(f"Configuration loaded from {self.config_file}")
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration file."""
        # Database configuration
        self.config['DATABASE'] = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'your_password'),
            'database': os.getenv('DB_NAME', 'weblogs_db'),
            'port': os.getenv('DB_PORT', '3306')
        }
        
        # Application settings
        self.config['APPLICATION'] = {
            'default_batch_size': '1000',
            'log_level': 'INFO',
            'max_file_size_mb': '100',
            'date_format': '%Y-%m-%d',
            'datetime_format': '%Y-%m-%d %H:%M:%S'
        }
        
        # Log file patterns
        self.config['LOG_PATTERNS'] = {
            'apache_common': r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - - \[(.*?)\] "(.*?)" (\d{3}) (\d+|-) "(.*?)" "(.*?)"',
            'apache_combined': r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - - \[(.*?)\] "(.*?)" (\d{3}) (\d+|-) "(.*?)" "(.*?)"'
        }
        
        # Performance settings
        self.config['PERFORMANCE'] = {
            'batch_size': '1000',
            'connection_timeout': '30',
            'query_timeout': '60',
            'max_connections': '10'
        }
        
        # Monitoring settings
        self.config['MONITORING'] = {
            'tail_interval': '5',
            'alert_error_threshold': '100',
            'alert_time_window': '300'
        }
        
        self._save_config()
        logging.info(f"Default configuration created: {self.config_file}")
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
        except Exception as e:
            logging.error(f"Error saving configuration: {str(e)}")
    
    def get_database_config(self) -> dict:
        """
        Get database configuration.
        
        Returns:
            dict: Database configuration parameters
        """
        return {
            'host': self.config.get('DATABASE', 'host'),
            'user': self.config.get('DATABASE', 'user'),
            'password': self.config.get('DATABASE', 'password'),
            'database': self.config.get('DATABASE', 'database'),
            'port': int(self.config.get('DATABASE', 'port'))
        }
    
    def get_application_config(self) -> dict:
        """
        Get application configuration.
        
        Returns:
            dict: Application configuration parameters
        """
        return {
            'default_batch_size': int(self.config.get('APPLICATION', 'default_batch_size')),
            'log_level': self.config.get('APPLICATION', 'log_level'),
            'max_file_size_mb': int(self.config.get('APPLICATION', 'max_file_size_mb')),
            'date_format': self.config.get('APPLICATION', 'date_format'),
            'datetime_format': self.config.get('APPLICATION', 'datetime_format')
        }
    
    def get_log_pattern(self, pattern_name='apache_common') -> str:
        """
        Get log file pattern.
        
        Args:
            pattern_name (str): Name of the pattern
            
        Returns:
            str: Regular expression pattern
        """
        return self.config.get('LOG_PATTERNS', pattern_name)
    
    def get_performance_config(self) -> dict:
        """
        Get performance configuration.
        
        Returns:
            dict: Performance configuration parameters
        """
        return {
            'batch_size': int(self.config.get('PERFORMANCE', 'batch_size')),
            'connection_timeout': int(self.config.get('PERFORMANCE', 'connection_timeout')),
            'query_timeout': int(self.config.get('PERFORMANCE', 'query_timeout')),
            'max_connections': int(self.config.get('PERFORMANCE', 'max_connections'))
        }
    
    def get_monitoring_config(self) -> dict:
        """
        Get monitoring configuration.
        
        Returns:
            dict: Monitoring configuration parameters
        """
        return {
            'tail_interval': int(self.config.get('MONITORING', 'tail_interval')),
            'alert_error_threshold': int(self.config.get('MONITORING', 'alert_error_threshold')),
            'alert_time_window': int(self.config.get('MONITORING', 'alert_time_window'))
        }
    
    def update_database_config(self, **kwargs):
        """
        Update database configuration.
        
        Args:
            **kwargs: Database configuration parameters to update
        """
        for key, value in kwargs.items():
            if key in ['host', 'user', 'password', 'database', 'port']:
                self.config.set('DATABASE', key, str(value))
        self._save_config()
        logging.info("Database configuration updated")
    
    def update_application_config(self, **kwargs):
        """
        Update application configuration.
        
        Args:
            **kwargs: Application configuration parameters to update
        """
        for key, value in kwargs.items():
            if key in self.config['APPLICATION']:
                self.config.set('APPLICATION', key, str(value))
        self._save_config()
        logging.info("Application configuration updated")
    
    def validate_config(self) -> bool:
        """
        Validate configuration parameters.
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Validate database config
            db_config = self.get_database_config()
            required_db_fields = ['host', 'user', 'password', 'database']
            for field in required_db_fields:
                if not db_config.get(field):
                    logging.error(f"Missing required database field: {field}")
                    return False
            
            # Validate port
            if not (1 <= db_config['port'] <= 65535):
                logging.error("Invalid database port number")
                return False
            
            # Validate application config
            app_config = self.get_application_config()
            if app_config['default_batch_size'] <= 0:
                logging.error("Invalid batch size")
                return False
            
            if app_config['max_file_size_mb'] <= 0:
                logging.error("Invalid max file size")
                return False
            
            logging.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logging.error(f"Configuration validation failed: {str(e)}")
            return False
    
    def get_all_config(self) -> dict:
        """
        Get all configuration as dictionary.
        
        Returns:
            dict: Complete configuration
        """
        return {
            'database': self.get_database_config(),
            'application': self.get_application_config(),
            'performance': self.get_performance_config(),
            'monitoring': self.get_monitoring_config()
        }
    
    def print_config(self, hide_password=True):
        """
        Print current configuration.
        
        Args:
            hide_password (bool): Whether to hide password in output
        """
        print("Current Configuration:")
        print("=" * 50)
        
        for section in self.config.sections():
            print(f"\n[{section}]")
            for key, value in self.config[section].items():
                if hide_password and key.lower() == 'password':
                    value = '*' * len(value)
                print(f"  {key} = {value}")


# Environment variable loader
def load_from_env():
    """Load configuration from environment variables."""
    env_config = {}
    
    # Database environment variables
    env_vars = {
        'DB_HOST': 'host',
        'DB_USER': 'user', 
        'DB_PASSWORD': 'password',
        'DB_NAME': 'database',
        'DB_PORT': 'port'
    }
    
    for env_var, config_key in env_vars.items():
        value = os.getenv(env_var)
        if value:
            env_config[config_key] = value
    
    return env_config


# Test function
def test_config():
    """Test configuration management."""
    print("Testing Configuration Management:")
    print("-" * 40)
    
    # Create config instance
    config = Config('test_config.ini')
    
    # Test validation
    is_valid = config.validate_config()
    print(f"✓ Configuration validation: {'PASSED' if is_valid else 'FAILED'}")
    
    # Test getting configurations
    db_config = config.get_database_config()
    print(f"✓ Database config loaded: {len(db_config)} parameters")
    
    app_config = config.get_application_config()
    print(f"✓ Application config loaded: {len(app_config)} parameters")
    
    # Test updating configuration
    config.update_application_config(default_batch_size=2000)
    updated_config = config.get_application_config()
    print(f"✓ Configuration updated: batch_size = {updated_config['default_batch_size']}")
    
    # Print configuration (hiding password)
    config.print_config()
    
    # Clean up test file
    if os.path.exists('test_config.ini'):
        os.remove('test_config.ini')
        print("✓ Test configuration file cleaned up")


if __name__ == "__main__":
    test_config()