#!/usr/bin/env python3
"""Google Sheets CSV Uploader - Main script for uploading CSV files to Google Sheets."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.single_instance import SingleInstance
from radiator.services.csv_file_monitor import CSVFileMonitor
from radiator.services.csv_processor import CSVProcessor
from radiator.services.google_sheets_config import GoogleSheetsConfig
from radiator.services.google_sheets_service import GoogleSheetsService


class GoogleSheetsCSVUploader:
    """Main class for Google Sheets CSV uploader."""

    def __init__(self):
        """Initialize the uploader."""
        self.config = GoogleSheetsConfig()
        self.sheets_service = None
        self.file_monitor = CSVFileMonitor()
        self.csv_processor = CSVProcessor()
        self.reports_dir = self.config.get_reports_dir()
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration."""
        # Ensure log directory exists
        self.config.ensure_log_directory()

        # Configure logging
        log_level = getattr(logging, self.config.LOG_LEVEL.upper(), logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Setup file handler
        file_handler = logging.FileHandler(self.config.LOG_FILE, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)

        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Reduce noise from google libraries
        logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
        logging.getLogger("google.auth").setLevel(logging.WARNING)

    def initialize_services(self) -> bool:
        """Initialize Google Sheets service."""
        try:
            credentials_path = self.config.get_absolute_credentials_path()
            self.sheets_service = GoogleSheetsService(
                credentials_path=credentials_path,
                document_id=self.config.DOCUMENT_ID,
                sheet_prefix=self.config.SHEET_PREFIX,
            )
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Google Sheets service: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to Google Sheets."""
        if not self.sheets_service:
            logging.error("Google Sheets service not initialized")
            return False

        return self.sheets_service.test_connection()

    def process_single_file(self, file_path: Path) -> bool:
        """
        Process a single CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            logging.info(f"Processing file: {file_path.name}")

            # Validate file
            validation = self.csv_processor.validate_file(file_path)
            if not validation["valid"]:
                logging.error(f"File validation failed: {validation['errors']}")
                return False

            # Process CSV
            df = self.csv_processor.process_csv(file_path)
            if df is None:
                logging.error(f"Failed to process CSV file: {file_path.name}")
                return False

            # Upload to Google Sheets
            success = self.sheets_service.upload_csv_to_sheet(file_path)
            if success:
                logging.info(f"Successfully uploaded {file_path.name} to Google Sheets")
                return True
            else:
                logging.error(f"Failed to upload {file_path.name} to Google Sheets")
                return False

        except Exception as e:
            logging.error(f"Error processing file {file_path.name}: {e}")
            return False

    def process_all_files(self) -> Dict[str, int]:
        """
        Process all unprocessed CSV files.

        Returns:
            Dictionary with processing statistics
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}

        # Get unprocessed files
        unprocessed_files = self.file_monitor.get_unprocessed_files()

        if not unprocessed_files:
            logging.info("No unprocessed files found")
            return stats

        logging.info(f"Found {len(unprocessed_files)} unprocessed files")

        for filename in unprocessed_files:
            file_path = self.file_monitor.get_file_path(filename)
            if not file_path:
                logging.warning(f"File not found: {filename}")
                stats["skipped"] += 1
                continue

            # Process file
            success = self.process_single_file(file_path)

            if success:
                self.file_monitor.mark_file_processed(filename)
                stats["processed"] += 1
            else:
                self.file_monitor.mark_file_failed(filename, "Processing failed")
                stats["failed"] += 1

        return stats

    def process_file_with_pivots(self, file_path: Path) -> bool:
        """
        Process a single CSV file and upload to Google Sheets with pivot tables.

        Args:
            file_path: Path to the CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            logging.info(f"Processing file with pivots: {file_path.name}")

            # Validate file
            validation = self.csv_processor.validate_file(file_path)
            if not validation["valid"]:
                logging.error(f"File validation failed: {validation['errors']}")
                return False

            # Process CSV
            df = self.csv_processor.process_csv(file_path)
            if df is None:
                logging.error(f"Failed to process CSV file: {file_path.name}")
                return False

            # Upload to Google Sheets
            success = self.sheets_service.upload_csv_to_sheet(file_path)
            if not success:
                logging.error(f"Failed to upload {file_path.name} to Google Sheets")
                return False

            # Create pivot tables using the DataFrame data
            pivot_results = self.sheets_service.create_pivot_tables_from_dataframe(
                df, self.sheets_service.document_id
            )

            if pivot_results["ttd_pivot"] is None or pivot_results["ttm_pivot"] is None:
                logging.error(f"Failed to create pivot tables for {file_path.name}")
                return False

            logging.info(
                f"Successfully uploaded {file_path.name} with pivot tables to Google Sheets"
            )
            return True

        except Exception as e:
            logging.error(f"Error processing file with pivots {file_path.name}: {e}")
            return False

    def process_files_with_markers(self) -> Dict[str, int]:
        """
        Process only CSV files that have upload markers (requested via Telegram).

        Returns:
            Dictionary with processing statistics
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}

        # Get files with upload markers
        files_with_markers = self.file_monitor.get_files_with_upload_markers()

        if not files_with_markers:
            logging.info("No files with upload markers found")
            return stats

        logging.info(f"Found {len(files_with_markers)} files with upload markers")

        for filename in files_with_markers:
            file_path = self.file_monitor.get_file_path(filename)
            if not file_path:
                logging.warning(f"File not found: {filename}")
                stats["skipped"] += 1
                continue

            # Process file
            success = self.process_single_file(file_path)

            if success:
                # Mark as processed and remove marker
                self.file_monitor.mark_file_processed(filename)
                self.file_monitor.remove_upload_marker(filename)
                stats["processed"] += 1
                logging.info(
                    f"Successfully processed and removed marker for {filename}"
                )
            else:
                self.file_monitor.mark_file_failed(filename, "Processing failed")
                stats["failed"] += 1

        return stats

    def process_files_with_pivot_markers(self) -> Dict[str, int]:
        """
        Process only CSV files that have pivot upload markers (requested via Telegram).

        Returns:
            Dictionary with processing statistics
        """
        stats = {"processed": 0, "failed": 0, "skipped": 0}

        # Get files with pivot upload markers
        files_with_markers = self.file_monitor.get_files_with_pivot_markers()

        if not files_with_markers:
            logging.info("No files with pivot upload markers found")
            return stats

        logging.info(f"Found {len(files_with_markers)} files with pivot upload markers")

        for filename in files_with_markers:
            file_path = self.reports_dir / filename

            if not file_path.exists():
                logging.warning(f"File {filename} no longer exists, skipping")
                stats["skipped"] += 1
                continue

            # Process file with pivots
            if self.process_file_with_pivots(file_path):
                # Mark as processed and remove marker
                self.file_monitor.mark_file_processed(filename)
                self.file_monitor.remove_pivot_upload_marker(filename)
                logging.info(
                    f"Successfully processed and removed pivot marker for {filename}"
                )
                stats["processed"] += 1
            else:
                self.file_monitor.mark_file_failed(
                    filename, "Processing with pivots failed"
                )
                stats["failed"] += 1

        return stats

    def start_monitoring(self):
        """Start continuous monitoring of CSV files with upload markers."""
        logging.info("Starting CSV file monitoring for files with upload markers...")

        # Check for single instance
        try:
            with SingleInstance("google_sheets_uploader"):
                logging.info("Google Sheets uploader instance lock acquired")

                try:
                    while True:
                        # Check for files with upload markers
                        files_with_markers = (
                            self.file_monitor.get_files_with_upload_markers()
                        )

                        if files_with_markers:
                            logging.info(
                                f"Found {len(files_with_markers)} files with upload markers"
                            )

                            for filename in files_with_markers:
                                file_path = self.file_monitor.get_file_path(filename)
                                if file_path:
                                    success = self.process_single_file(file_path)
                                    if success:
                                        self.file_monitor.mark_file_processed(filename)
                                        self.file_monitor.remove_upload_marker(filename)
                                        logging.info(
                                            f"Successfully processed and removed marker for {filename}"
                                        )
                                    else:
                                        self.file_monitor.mark_file_failed(
                                            filename, "Processing failed"
                                        )

                        # Check for files with pivot upload markers
                        files_with_pivot_markers = (
                            self.file_monitor.get_files_with_pivot_markers()
                        )

                        if files_with_pivot_markers:
                            logging.info(
                                f"Found {len(files_with_pivot_markers)} files with pivot upload markers"
                            )

                            for filename in files_with_pivot_markers:
                                file_path = self.file_monitor.get_file_path(filename)
                                if file_path:
                                    success = self.process_file_with_pivots(file_path)
                                    if success:
                                        self.file_monitor.mark_file_processed(filename)
                                        self.file_monitor.remove_pivot_upload_marker(
                                            filename
                                        )
                                        logging.info(
                                            f"Successfully processed and removed pivot marker for {filename}"
                                        )
                                    else:
                                        self.file_monitor.mark_file_failed(
                                            filename, "Processing with pivots failed"
                                        )

                        if not files_with_markers and not files_with_pivot_markers:
                            logging.debug("No files with upload markers found")

                        # Cleanup old records
                        self.file_monitor.cleanup_old_files()

                        # Wait before next check
                        import time

                        time.sleep(self.config.POLLING_INTERVAL)

                except KeyboardInterrupt:
                    logging.info("Monitoring stopped by user")
                except Exception as e:
                    logging.error(f"Monitoring error: {e}")
        except RuntimeError as e:
            logging.error(f"Failed to start Google Sheets uploader: {e}")
            sys.exit(1)

    def show_stats(self):
        """Show monitoring statistics."""
        stats = self.file_monitor.get_stats()
        files_with_markers = self.file_monitor.get_files_with_upload_markers()

        print(f"CSV File Monitor Statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Known files: {stats['known_files']}")
        print(f"  Processed files: {stats['processed_files']}")
        print(f"  Unprocessed files: {stats['unprocessed_files']}")
        print(f"  Files with upload markers: {len(files_with_markers)}")

        if files_with_markers:
            print(f"\nFiles ready for Google Sheets upload:")
            for filename in files_with_markers:
                print(f"  - {filename}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Google Sheets CSV Uploader")
    parser.add_argument(
        "--test", action="store_true", help="Test connection to Google Sheets"
    )
    parser.add_argument(
        "--process-all", action="store_true", help="Process all unprocessed files"
    )
    parser.add_argument(
        "--process-markers",
        action="store_true",
        help="Process files with upload markers (from Telegram)",
    )
    parser.add_argument(
        "--process-pivot-markers",
        action="store_true",
        help="Process files with pivot upload markers (from Telegram)",
    )
    parser.add_argument("--process-file", type=str, help="Process specific CSV file")
    parser.add_argument(
        "--monitor", action="store_true", help="Start continuous monitoring"
    )
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--config", action="store_true", help="Show configuration")
    parser.add_argument(
        "--cleanup", action="store_true", help="Cleanup old file records"
    )

    args = parser.parse_args()

    # Initialize uploader
    uploader = GoogleSheetsCSVUploader()

    # Validate configuration
    if not uploader.config.validate():
        sys.exit(1)

    # Show configuration if requested
    if args.config:
        uploader.config.print_config()
        return

    # Initialize services
    if not uploader.initialize_services():
        sys.exit(1)

    # Test connection if requested
    if args.test:
        if uploader.test_connection():
            print("✅ Connection to Google Sheets successful")
        else:
            print("❌ Connection to Google Sheets failed")
            sys.exit(1)
        return

    # Show stats if requested
    if args.stats:
        uploader.show_stats()
        return

    # Cleanup if requested
    if args.cleanup:
        uploader.file_monitor.cleanup_old_files()
        print("✅ Cleanup completed")
        return

    # Process specific file if requested
    if args.process_file:
        file_path = Path(args.process_file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)

        success = uploader.process_single_file(file_path)
        if success:
            print(f"✅ Successfully processed {file_path.name}")
        else:
            print(f"❌ Failed to process {file_path.name}")
            sys.exit(1)
        return

    # Process all files if requested
    if args.process_all:
        stats = uploader.process_all_files()
        print(f"Processing completed:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")
        return

    # Process files with markers if requested
    if args.process_markers:
        stats = uploader.process_files_with_markers()
        print(f"Processing files with upload markers completed:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")
        return

    # Process files with pivot markers if requested
    if args.process_pivot_markers:
        stats = uploader.process_files_with_pivot_markers()
        print(f"Processing files with pivot upload markers completed:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")
        return

    # Start monitoring if requested
    if args.monitor:
        uploader.start_monitoring()
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
