"""
Logging utilities for the ND Court Rules Scraper.
Provides verbose debugging capabilities and configurable log levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import yaml


class ScraperLogger:
    """Custom logger for the scraper with verbose debugging capabilities."""
    
    def __init__(self, config_path: str = "config.yaml", verbose: bool = False):
        """
        Initialize the logger with configuration.
        
        Args:
            config_path: Path to the configuration file
            verbose: Enable verbose logging regardless of config
        """
        self.config = self._load_config(config_path)
        self.verbose = verbose or self.config.get('logging', {}).get('verbose', False)
        self.logger = self._setup_logger()
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {config_path} not found. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            return {}
    
    def _setup_logger(self) -> logging.Logger:
        """Set up the logger with appropriate handlers and formatters."""
        logger = logging.getLogger('nd_courts_scraper')
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Set log level
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        if self.verbose:
            log_level = 'DEBUG'
        
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create formatters
        verbose_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
        
        # File handler for detailed logging
        log_file = self.config.get('logging', {}).get('log_file', 'scraper.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(verbose_formatter)
        logger.addHandler(file_handler)
        
        # Debug console handler for verbose output
        if self.verbose:
            debug_handler = logging.StreamHandler(sys.stdout)
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(verbose_formatter)
            logger.addHandler(debug_handler)
        
        return logger
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log critical message."""
        self.logger.critical(message)
    
    def log_request(self, url: str, method: str = "GET", status_code: Optional[int] = None):
        """Log HTTP request details."""
        if status_code:
            self.debug(f"HTTP {method} {url} - Status: {status_code}")
        else:
            self.debug(f"HTTP {method} {url}")
    
    def log_scraping_progress(self, category: str, current: int, total: int):
        """Log scraping progress for a category."""
        self.info(f"Scraping {category}: {current}/{total} rules processed")
    
    def log_rule_processing(self, rule_title: str, success: bool, error: Optional[str] = None):
        """Log individual rule processing results."""
        if success:
            self.debug(f"[OK] Successfully processed rule: {rule_title}")
        else:
            self.error(f"[ERROR] Failed to process rule: {rule_title} - {error}")
    
    def log_api_call(self, model: str, tokens_used: Optional[int] = None):
        """Log Anthropic API call details."""
        if tokens_used:
            self.debug(f"API call to {model} - Tokens used: {tokens_used}")
        else:
            self.debug(f"API call to {model}")
    
    def log_file_operation(self, operation: str, file_path: str, success: bool):
        """Log file operation results."""
        if success:
            self.debug(f"[OK] {operation}: {file_path}")
        else:
            self.error(f"[ERROR] {operation}: {file_path}")


def get_logger(config_path: str = "config.yaml", verbose: bool = False) -> ScraperLogger:
    """
    Get a configured logger instance.
    
    Args:
        config_path: Path to the configuration file
        verbose: Enable verbose logging
    
    Returns:
        Configured ScraperLogger instance
    """
    return ScraperLogger(config_path, verbose) 