"""
File utilities for the ND Court Rules Scraper.
Handles JSON file operations, directory management, and data persistence.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import yaml
from utils.logger import ScraperLogger


class FileManager:
    """Manages file operations for the scraper."""
    
    def __init__(self, config_path: str = "config.yaml", logger: Optional[ScraperLogger] = None):
        """
        Initialize the file manager.
        
        Args:
            config_path: Path to configuration file
            logger: Logger instance
        """
        self.config = self._load_config(config_path)
        self.logger = logger or ScraperLogger(config_path)
        self._setup_directories()
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing config file: {e}")
            return {}
    
    def _setup_directories(self):
        """Create necessary directories for data storage."""
        output_config = self.config.get('output', {})
        
        directories = [
            output_config.get('data_dir', 'data'),
            output_config.get('raw_dir', 'data/raw'),
            output_config.get('processed_dir', 'data/processed'),
            output_config.get('metadata_dir', 'data/metadata'),
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {directory}")
    
    def save_json(self, data: Dict[str, Any], filename: str, directory: str = "processed") -> bool:
        """
        Save data to JSON file with proper formatting.
        
        Args:
            data: Data to save
            filename: Name of the file (without extension)
            directory: Directory to save in (relative to data dir)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            output_config = self.config.get('output', {})
            base_dir = output_config.get('data_dir', 'data')
            file_path = Path(base_dir) / directory / f"{filename}.json"
            
            # Add metadata
            data_with_metadata = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "source": "ND Courts Rules Scraper",
                    "version": "1.0"
                },
                "data": data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_with_metadata, f, indent=2, ensure_ascii=False)
            
            self.logger.log_file_operation("Saved JSON", str(file_path), True)
            return True
            
        except Exception as e:
            self.logger.log_file_operation("Save JSON", filename, False)
            self.logger.error(f"Error saving JSON file {filename}: {e}")
            return False
    
    def load_json(self, filename: str, directory: str = "processed") -> Optional[Dict[str, Any]]:
        """
        Load data from JSON file.
        
        Args:
            filename: Name of the file (without extension)
            directory: Directory to load from (relative to data dir)
        
        Returns:
            Loaded data or None if failed
        """
        try:
            output_config = self.config.get('output', {})
            base_dir = output_config.get('data_dir', 'data')
            file_path = Path(base_dir) / directory / f"{filename}.json"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.log_file_operation("Loaded JSON", str(file_path), True)
            return data
            
        except FileNotFoundError:
            self.logger.warning(f"JSON file not found: {filename}")
            return None
        except Exception as e:
            self.logger.log_file_operation("Load JSON", filename, False)
            self.logger.error(f"Error loading JSON file {filename}: {e}")
            return None
    
    def save_raw_html(self, html_content: str, filename: str) -> bool:
        """
        Save raw HTML content.
        
        Args:
            html_content: HTML content to save
            filename: Name of the file (without extension)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            output_config = self.config.get('output', {})
            raw_dir = output_config.get('raw_dir', 'data/raw')
            file_path = Path(raw_dir) / f"{filename}.html"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.log_file_operation("Saved HTML", str(file_path), True)
            return True
            
        except Exception as e:
            self.logger.log_file_operation("Save HTML", filename, False)
            self.logger.error(f"Error saving HTML file {filename}: {e}")
            return False
    
    def save_metadata(self, metadata: Dict[str, Any], filename: str) -> bool:
        """
        Save scraping metadata.
        
        Args:
            metadata: Metadata to save
            filename: Name of the file (without extension)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            output_config = self.config.get('output', {})
            metadata_dir = output_config.get('metadata_dir', 'data/metadata')
            file_path = Path(metadata_dir) / f"{filename}.json"
            
            # Add timestamp
            metadata_with_timestamp = {
                "timestamp": datetime.now().isoformat(),
                **metadata
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_with_timestamp, f, indent=2, ensure_ascii=False)
            
            self.logger.log_file_operation("Saved metadata", str(file_path), True)
            return True
            
        except Exception as e:
            self.logger.log_file_operation("Save metadata", filename, False)
            self.logger.error(f"Error saving metadata file {filename}: {e}")
            return False
    
    def get_file_list(self, directory: str = "processed", extension: str = ".json") -> List[str]:
        """
        Get list of files in a directory.
        
        Args:
            directory: Directory to search (relative to data dir)
            extension: File extension to filter by
        
        Returns:
            List of filenames
        """
        try:
            output_config = self.config.get('output', {})
            base_dir = output_config.get('data_dir', 'data')
            dir_path = Path(base_dir) / directory
            
            if not dir_path.exists():
                return []
            
            files = [f.stem for f in dir_path.glob(f"*{extension}")]
            self.logger.debug(f"Found {len(files)} files in {directory}")
            return files
            
        except Exception as e:
            self.logger.error(f"Error listing files in {directory}: {e}")
            return []
    
    def file_exists(self, filename: str, directory: str = "processed") -> bool:
        """
        Check if a file exists.
        
        Args:
            filename: Name of the file (without extension)
            directory: Directory to check (relative to data dir)
        
        Returns:
            True if file exists, False otherwise
        """
        output_config = self.config.get('output', {})
        base_dir = output_config.get('data_dir', 'data')
        file_path = Path(base_dir) / directory / f"{filename}.json"
        return file_path.exists()
    
    def get_file_size(self, filename: str, directory: str = "processed") -> Optional[int]:
        """
        Get file size in bytes.
        
        Args:
            filename: Name of the file (without extension)
            directory: Directory to check (relative to data dir)
        
        Returns:
            File size in bytes or None if file doesn't exist
        """
        output_config = self.config.get('output', {})
        base_dir = output_config.get('data_dir', 'data')
        file_path = Path(base_dir) / directory / f"{filename}.json"
        
        if file_path.exists():
            return file_path.stat().st_size
        return None
    
    def cleanup_old_files(self, directory: str = "raw", days_old: int = 7) -> int:
        """
        Clean up old files in a directory.
        
        Args:
            directory: Directory to clean (relative to data dir)
            days_old: Remove files older than this many days
        
        Returns:
            Number of files removed
        """
        try:
            from datetime import timedelta
            
            output_config = self.config.get('output', {})
            base_dir = output_config.get('data_dir', 'data')
            dir_path = Path(base_dir) / directory
            
            if not dir_path.exists():
                return 0
            
            cutoff_time = datetime.now() - timedelta(days=days_old)
            removed_count = 0
            
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
                        self.logger.debug(f"Removed old file: {file_path}")
            
            self.logger.info(f"Cleaned up {removed_count} old files from {directory}")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old files in {directory}: {e}")
            return 0 