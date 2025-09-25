"""CSV file processor for Google Sheets integration."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd

logger = logging.getLogger(__name__)


class CSVProcessor:
    """Processor for CSV files before uploading to Google Sheets."""
    
    def __init__(self):
        """Initialize CSV processor."""
        self.supported_encodings = ['utf-8', 'utf-8-sig', 'windows-1251', 'cp1251', 'iso-8859-1']
        self.max_rows = 1000000  # Google Sheets limit
        self.max_columns = 1000  # Google Sheets limit
    
    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate CSV file before processing.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        try:
            # Check if file exists
            if not file_path.exists():
                result['errors'].append(f"File does not exist: {file_path}")
                return result
            
            # Check file size
            file_size = file_path.stat().st_size
            result['info']['file_size'] = file_size
            
            if file_size == 0:
                result['errors'].append("File is empty")
                return result
            
            # Check file extension
            if file_path.suffix.lower() != '.csv':
                result['warnings'].append(f"File extension is not .csv: {file_path.suffix}")
            
            # Try to read file to check format
            df = self._read_csv_file(file_path)
            if df is None:
                result['errors'].append("Could not read CSV file with any supported encoding")
                return result
            
            # Check dimensions
            rows, cols = df.shape
            result['info']['rows'] = rows
            result['info']['columns'] = cols
            
            if rows > self.max_rows:
                result['errors'].append(f"Too many rows: {rows} (max: {self.max_rows})")
            
            if cols > self.max_columns:
                result['errors'].append(f"Too many columns: {cols} (max: {self.max_columns})")
            
            if rows == 0:
                result['errors'].append("CSV file has no data rows")
                return result
            
            # Check for empty column names
            empty_columns = df.columns[df.columns.isna() | (df.columns == '')].tolist()
            if empty_columns:
                result['warnings'].append(f"Found empty column names: {empty_columns}")
            
            # Check for duplicate column names
            duplicate_columns = df.columns[df.columns.duplicated()].tolist()
            if duplicate_columns:
                result['warnings'].append(f"Found duplicate column names: {duplicate_columns}")
            
            result['valid'] = len(result['errors']) == 0
            result['info']['dataframe'] = df
            
        except Exception as e:
            result['errors'].append(f"Unexpected error during validation: {e}")
            logger.error(f"Error validating CSV file {file_path}: {e}")
        
        return result
    
    def _read_csv_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """
        Read CSV file with multiple encoding attempts.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame or None if failed
        """
        for encoding in self.supported_encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                logger.debug(f"Successfully read CSV file {file_path.name} with encoding {encoding}")
                return df
            except UnicodeDecodeError:
                logger.debug(f"Failed to read {file_path.name} with encoding {encoding}")
                continue
            except Exception as e:
                logger.debug(f"Error reading CSV file {file_path.name} with encoding {encoding}: {e}")
                continue
        
        return None
    
    def process_csv(self, file_path: Path) -> Optional[pd.DataFrame]:
        """
        Process CSV file for Google Sheets upload.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Processed DataFrame or None if failed
        """
        try:
            # Validate file first
            validation = self.validate_file(file_path)
            if not validation['valid']:
                logger.error(f"CSV file validation failed for {file_path.name}: {validation['errors']}")
                return None
            
            df = validation['info']['dataframe']
            
            # Process the DataFrame
            df = self._clean_dataframe(df)
            
            logger.info(f"Successfully processed CSV file {file_path.name}: {df.shape[0]} rows, {df.shape[1]} columns")
            return df
            
        except Exception as e:
            logger.error(f"Error processing CSV file {file_path}: {e}")
            return None
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean DataFrame for Google Sheets compatibility.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Create a copy to avoid modifying original
        df_clean = df.copy()
        
        # Fix column names
        df_clean.columns = self._clean_column_names(df_clean.columns)
        
        # Handle missing values
        df_clean = df_clean.fillna('')
        
        # Convert data types to be Google Sheets compatible
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                # Convert to string and handle special characters
                df_clean[col] = df_clean[col].astype(str)
                # Remove or replace problematic characters
                df_clean[col] = df_clean[col].str.replace('\x00', '', regex=False)  # Remove null bytes
        
        return df_clean
    
    def _clean_column_names(self, columns: pd.Index) -> List[str]:
        """
        Clean column names for Google Sheets compatibility.
        
        Args:
            columns: Original column names
            
        Returns:
            List of cleaned column names
        """
        cleaned = []
        seen = set()
        
        for i, col in enumerate(columns):
            if pd.isna(col) or col == '':
                # Generate name for empty column
                name = f"Column_{i+1}"
            else:
                # Convert to string and clean
                name = str(col).strip()
                
                # Remove or replace problematic characters
                name = name.replace('\x00', '')  # Remove null bytes
                name = name.replace('\n', ' ')   # Replace newlines
                name = name.replace('\r', ' ')   # Replace carriage returns
            
            # Ensure uniqueness
            original_name = name
            counter = 1
            while name in seen:
                name = f"{original_name}_{counter}"
                counter += 1
            
            cleaned.append(name)
            seen.add(name)
        
        return cleaned
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get information about CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Dictionary with file information
        """
        info = {
            'filename': file_path.name,
            'size': 0,
            'rows': 0,
            'columns': 0,
            'encoding': None,
            'valid': False
        }
        
        try:
            if file_path.exists():
                info['size'] = file_path.stat().st_size
                
                # Try to read file to get dimensions
                df = self._read_csv_file(file_path)
                if df is not None:
                    info['rows'] = df.shape[0]
                    info['columns'] = df.shape[1]
                    info['valid'] = True
                    
                    # Try to determine encoding
                    for encoding in self.supported_encodings:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                f.read(1000)  # Read first 1000 characters
                            info['encoding'] = encoding
                            break
                        except UnicodeDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
        
        return info
