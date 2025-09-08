"""Tests for GenerateTimeToMarketReportCommand."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np

from radiator.commands.generate_time_to_market_report import GenerateTimeToMarketReportCommand
from radiator.models.tracker import TrackerTask, TrackerTaskHistory


class TestGenerateTimeToMarketReportCommand:
    """Test cases for GenerateTimeToMarketReportCommand."""

    def test_init(self):
        """Test command initialization."""
        cmd = GenerateTimeToMarketReportCommand()
        assert cmd.db is not None
        assert cmd.group_by == "author"
        assert cmd.report_data == {}

    def test_init_with_team_grouping(self):
        """Test command initialization with team grouping."""
        cmd = GenerateTimeToMarketReportCommand(group_by="team")
        assert cmd.group_by == "team"

    def test_init_invalid_grouping(self):
        """Test command initialization with invalid grouping."""
        with pytest.raises(ValueError, match="group_by must be 'author' or 'team'"):
            GenerateTimeToMarketReportCommand(group_by="invalid")

    def test_context_manager(self):
        """Test context manager functionality."""
        with GenerateTimeToMarketReportCommand() as cmd:
            assert cmd.db is not None
        # db should be closed after context exit

    def test_load_quarters_success(self):
        """Test successful loading of quarters from file."""
        cmd = GenerateTimeToMarketReportCommand()
        
        mock_content = [
            "2025.Q1;2025-01-27;2025-04-20",
            "2025.Q2;2025-04-21;2025-07-20",
            "2025.Q3;2025-07-21;2025-10-12"
        ]
        
        with patch('builtins.open', mock_open(read_data='\n'.join(mock_content))):
            result = cmd._load_quarters()
            
            expected = [
                {
                    'name': '2025.Q1',
                    'start_date': datetime(2025, 1, 27),
                    'end_date': datetime(2025, 4, 20)
                },
                {
                    'name': '2025.Q2', 
                    'start_date': datetime(2025, 4, 21),
                    'end_date': datetime(2025, 7, 20)
                },
                {
                    'name': '2025.Q3',
                    'start_date': datetime(2025, 7, 21),
                    'end_date': datetime(2025, 10, 12)
                }
            ]
            assert result == expected

    def test_load_quarters_file_not_found(self):
        """Test handling when quarters file is not found."""
        cmd = GenerateTimeToMarketReportCommand()
        
        with patch('pathlib.Path.exists', return_value=False):
            result = cmd._load_quarters()
            assert result == []

    def test_load_quarters_parsing_error(self):
        """Test handling of malformed lines in quarters file."""
        cmd = GenerateTimeToMarketReportCommand()
        
        mock_content = [
            "2025.Q1;2025-01-27;2025-04-20",
            "invalid_line_without_semicolons",
            "2025.Q2;2025-04-21;2025-07-20",
            "2025.Q3;invalid_date_format;2025-10-12"
        ]
        
        with patch('builtins.open', mock_open(read_data='\n'.join(mock_content))):
            result = cmd._load_quarters()
            
            # Should only include valid lines
            expected = [
                {
                    'name': '2025.Q1',
                    'start_date': datetime(2025, 1, 27),
                    'end_date': datetime(2025, 4, 20)
                },
                {
                    'name': '2025.Q2',
                    'start_date': datetime(2025, 4, 21),
                    'end_date': datetime(2025, 7, 20)
                }
            ]
            assert result == expected

    def test_load_status_mapping_success(self):
        """Test successful loading of status mapping from file."""
        cmd = GenerateTimeToMarketReportCommand()
        
        mock_content = [
            "Открыт;backlog",
            "В работе;discovery",
            "Готова к разработке;discovery",
            "МП / В работе;delivery",
            "Выполнено с ИТ;done",
            "Закрыт;done"
        ]
        
        with patch('builtins.open', mock_open(read_data='\n'.join(mock_content))):
            result = cmd._load_status_mapping()
            
            expected = {
                "Открыт": "backlog",
                "В работе": "discovery",
                "Готова к разработке": "discovery",
                "МП / В работе": "delivery",
                "Выполнено с ИТ": "done",
                "Закрыт": "done"
            }
            assert result == expected

    def test_get_target_statuses(self):
        """Test extraction of target statuses by block."""
        cmd = GenerateTimeToMarketReportCommand()
        
        status_mapping = {
            "Открыт": "backlog",
            "В работе": "discovery",
            "Готова к разработке": "discovery",
            "МП / В работе": "delivery",
            "Выполнено с ИТ": "done",
            "Закрыт": "done",
            "Отменено": "done"
        }
        
        result = cmd._get_target_statuses(status_mapping)
        
        expected = {
            'discovery': ["В работе", "Готова к разработке"],
            'done': ["Выполнено с ИТ", "Закрыт", "Отменено"]
        }
        assert result == expected

    def test_calculate_time_to_delivery_success(self):
        """Test successful calculation of Time To Delivery."""
        cmd = GenerateTimeToMarketReportCommand()
        
        # Mock task data
        task_created_at = datetime(2025, 1, 15)
        discovery_status_date = datetime(2025, 1, 20)
        
        # Mock history data
        history_data = [
            {
                'status': 'Открыт',
                'start_date': task_created_at,
                'end_date': datetime(2025, 1, 16)
            },
            {
                'status': 'В работе',
                'start_date': datetime(2025, 1, 16),
                'end_date': discovery_status_date
            },
            {
                'status': 'Готова к разработке',
                'start_date': discovery_status_date,
                'end_date': None
            }
        ]
        
        target_statuses = ['В работе', 'Готова к разработке']
        
        result = cmd._calculate_time_to_delivery(task_created_at, history_data, target_statuses)
        
        # Should return 1 day (from 2025-01-15 to 2025-01-16, first discovery status)
        assert result == 1

    def test_calculate_time_to_delivery_no_target_status(self):
        """Test calculation when task never reaches target status."""
        cmd = GenerateTimeToMarketReportCommand()
        
        task_created_at = datetime(2025, 1, 15)
        history_data = [
            {
                'status': 'Открыт',
                'start_date': task_created_at,
                'end_date': None
            }
        ]
        target_statuses = ['Готова к разработке']
        
        result = cmd._calculate_time_to_delivery(task_created_at, history_data, target_statuses)
        
        assert result is None

    def test_calculate_time_to_market_success(self):
        """Test successful calculation of Time To Market."""
        cmd = GenerateTimeToMarketReportCommand()
        
        task_created_at = datetime(2025, 1, 15)
        done_status_date = datetime(2025, 3, 15)
        
        history_data = [
            {
                'status': 'Открыт',
                'start_date': task_created_at,
                'end_date': datetime(2025, 1, 16)
            },
            {
                'status': 'В работе',
                'start_date': datetime(2025, 1, 16),
                'end_date': datetime(2025, 2, 1)
            },
            {
                'status': 'МП / В работе',
                'start_date': datetime(2025, 2, 1),
                'end_date': done_status_date
            },
            {
                'status': 'Выполнено с ИТ',
                'start_date': done_status_date,
                'end_date': None
            }
        ]
        
        target_statuses = ['Выполнено с ИТ', 'Закрыт', 'Отменено']
        
        result = cmd._calculate_time_to_market(task_created_at, history_data, target_statuses)
        
        # Should return 59 days (from 2025-01-15 to 2025-03-15)
        assert result == 59

    def test_calculate_statistics(self):
        """Test calculation of mean and 85th percentile."""
        cmd = GenerateTimeToMarketReportCommand()
        
        # Test data: [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
        times = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
        
        result = cmd._calculate_statistics(times)
        
        expected_mean = np.mean(times)  # 27.5
        expected_p85 = np.percentile(times, 85)  # 47.5
        
        assert result['mean'] == pytest.approx(expected_mean, rel=1e-10)
        assert result['p85'] == pytest.approx(expected_p85, rel=1e-10)

    def test_calculate_statistics_empty_list(self):
        """Test calculation with empty list."""
        cmd = GenerateTimeToMarketReportCommand()
        
        result = cmd._calculate_statistics([])
        
        assert result['mean'] is None
        assert result['p85'] is None

    def test_get_tasks_for_period_success(self):
        """Test successful retrieval of tasks for a specific period."""
        cmd = GenerateTimeToMarketReportCommand()
        
        # Mock database query results
        mock_tasks = [
            (1, "CPO-123", "Иван Иванов", datetime(2025, 1, 15)),
            (2, "CPO-456", "Петр Петров", datetime(2025, 2, 10)),
            (3, "CPO-789", "Иван Иванов", datetime(2025, 3, 5))
        ]
        
        # Mock status mapping
        mock_status_mapping = {
            'Готова к разработке': 'discovery',
            'Выполнено с ИТ': 'done'
        }
        
        with patch.object(cmd, '_load_status_mapping', return_value=mock_status_mapping), \
             patch.object(cmd.db, 'query') as mock_query:
            
            # Mock the complex query chain
            mock_query.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = mock_tasks
            
            start_date = datetime(2025, 1, 1)
            end_date = datetime(2025, 3, 31)
            
            result = cmd._get_tasks_for_period(start_date, end_date)
            
            expected = [
                {
                    'id': 1,
                    'key': 'CPO-123',
                    'group_value': 'Иван Иванов',
                    'author': 'Иван Иванов',
                    'team': None,
                    'created_at': datetime(2025, 1, 15)
                },
                {
                    'id': 2,
                    'key': 'CPO-456',
                    'group_value': 'Петр Петров',
                    'author': 'Петр Петров',
                    'team': None,
                    'created_at': datetime(2025, 2, 10)
                },
                {
                    'id': 3,
                    'key': 'CPO-789',
                    'group_value': 'Иван Иванов',
                    'author': 'Иван Иванов',
                    'team': None,
                    'created_at': datetime(2025, 3, 5)
                }
            ]
            assert result == expected

    def test_get_task_history_success(self):
        """Test successful retrieval of task history."""
        cmd = GenerateTimeToMarketReportCommand()
        
        # Mock history data
        mock_history = [
            ("Открыт", "Открыт", datetime(2025, 1, 15), datetime(2025, 1, 16)),
            ("В работе", "В работе", datetime(2025, 1, 16), datetime(2025, 1, 20)),
            ("Готова к разработке", "Готова к разработке", datetime(2025, 1, 20), None)
        ]
        
        with patch.object(cmd.db, 'query') as mock_query:
            mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_history
            
            result = cmd._get_task_history(1)
            
            expected = [
                {
                    'status': 'Открыт',
                    'status_display': 'Открыт',
                    'start_date': datetime(2025, 1, 15),
                    'end_date': datetime(2025, 1, 16)
                },
                {
                    'status': 'В работе',
                    'status_display': 'В работе',
                    'start_date': datetime(2025, 1, 16),
                    'end_date': datetime(2025, 1, 20)
                },
                {
                    'status': 'Готова к разработке',
                    'status_display': 'Готова к разработке',
                    'start_date': datetime(2025, 1, 20),
                    'end_date': None
                }
            ]
            assert result == expected

    def test_generate_report_data_success(self):
        """Test successful generation of report data."""
        cmd = GenerateTimeToMarketReportCommand()
        
        # Mock quarters data
        quarters = [
            {
                'name': '2025.Q1',
                'start_date': datetime(2025, 1, 1),
                'end_date': datetime(2025, 3, 31)
            }
        ]
        
        # Mock status mapping
        status_mapping = {
            "В работе": "discovery",
            "Готова к разработке": "discovery",
            "Выполнено с ИТ": "done"
        }
        
        # Mock tasks data
        tasks_data = [
            {
                'id': 1,
                'key': 'CPO-123',
                'group_value': 'Иван Иванов',
                'author': 'Иван Иванов',
                'team': 'Команда А',
                'created_at': datetime(2025, 1, 15)
            }
        ]
        
        # Mock history data
        history_data = [
            {
                'status': 'В работе',
                'start_date': datetime(2025, 1, 20),
                'end_date': datetime(2025, 2, 1)
            },
            {
                'status': 'Выполнено с ИТ',
                'start_date': datetime(2025, 3, 15),
                'end_date': None
            }
        ]
        
        with patch.object(cmd, '_load_quarters', return_value=quarters), \
             patch.object(cmd, '_load_status_mapping', return_value=status_mapping), \
             patch.object(cmd, '_get_tasks_for_period', return_value=tasks_data), \
             patch.object(cmd, '_get_task_history', return_value=history_data), \
             patch.object(cmd, '_calculate_time_to_delivery', return_value=5), \
             patch.object(cmd, '_calculate_time_to_market', return_value=59):
            
            result = cmd.generate_report_data()
            
            expected = {
                '2025.Q1': {
                    'Иван Иванов': {
                        'tasks_count': 2,  # 1 TTD + 1 TTM
                        'ttd_times': [5],
                        'ttm_times': [59],
                        'ttd_mean': 5.0,
                        'ttd_p85': 5.0,
                        'ttm_mean': 59.0,
                        'ttm_p85': 59.0
                    }
                }
            }
            assert result == expected

    def test_generate_report_data_no_data(self):
        """Test report generation when no data is available."""
        cmd = GenerateTimeToMarketReportCommand()
        
        with patch.object(cmd, '_load_quarters', return_value=[]):
            result = cmd.generate_report_data()
            assert result == {}

    def test_generate_csv_success(self):
        """Test successful CSV generation."""
        cmd = GenerateTimeToMarketReportCommand()
        
        # Mock report data
        cmd.report_data = {
            '2025.Q1': {
                'Иван Иванов': {
                    'tasks_count': 2,
                    'ttd_mean': 7.5,
                    'ttd_p85': 10.0,
                    'ttm_mean': 45.0,
                    'ttm_p85': 60.0
                },
                'Петр Петров': {
                    'tasks_count': 1,
                    'ttd_mean': 5.0,
                    'ttd_p85': 5.0,
                    'ttm_mean': 30.0,
                    'ttm_p85': 30.0
                }
            }
        }
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = cmd.generate_csv("test_report.csv")
            
            # Check that file was opened for writing
            mock_file.assert_called_once_with("test_report.csv", 'w', newline='', encoding='utf-8')
            assert result == "test_report.csv"

    def test_generate_table_success(self):
        """Test successful table generation."""
        cmd = GenerateTimeToMarketReportCommand()
        
        # Mock report data
        cmd.report_data = {
            '2025.Q1': {
                'Иван Иванов': {
                    'tasks_count': 2,
                    'ttd_mean': 7.5,
                    'ttd_p85': 10.0,
                    'ttm_mean': 45.0,
                    'ttm_p85': 60.0
                }
            }
        }
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig, \
             patch('matplotlib.pyplot.close') as mock_close:
            
            result = cmd.generate_table("test_table.png")
            
            mock_savefig.assert_called_once()
            mock_close.assert_called_once()
            assert result == "test_table.png"

    def test_print_summary_success(self):
        """Test successful summary printing."""
        cmd = GenerateTimeToMarketReportCommand()
        
        # Mock report data
        cmd.report_data = {
            '2025.Q1': {
                'Иван Иванов': {
                    'tasks_count': 2,
                    'ttd_mean': 7.5,
                    'ttd_p85': 10.0,
                    'ttm_mean': 45.0,
                    'ttm_p85': 60.0
                }
            }
        }
        
        with patch('builtins.print') as mock_print:
            cmd.print_summary()
            
            # Check that print was called multiple times
            assert mock_print.call_count > 0

    def test_print_summary_no_data(self):
        """Test summary printing when no data is available."""
        cmd = GenerateTimeToMarketReportCommand()
        
        with patch('builtins.print') as mock_print:
            cmd.print_summary()
            
            # Should print warning message
            mock_print.assert_called_with("No report data available. Run generate_report_data() first.")

    def test_main_function_success(self):
        """Test main function execution."""
        with patch('radiator.commands.generate_time_to_market_report.GenerateTimeToMarketReportCommand') as mock_cmd_class, \
             patch('sys.argv', ['generate_time_to_market_report.py']):
            
            mock_cmd = MagicMock()
            mock_cmd_class.return_value.__enter__.return_value = mock_cmd
            
            # Import and call main function
            from radiator.commands.generate_time_to_market_report import main
            main()
            
            # Check that command was created and methods were called
            mock_cmd_class.assert_called_once()
            mock_cmd.generate_report_data.assert_called_once()
            mock_cmd.generate_csv.assert_called_once()
            mock_cmd.generate_table.assert_called_once()
            mock_cmd.print_summary.assert_called_once()


class TestTimeToMarketReportIntegration:
    """Integration tests for Time To Market report."""

    def test_full_workflow_author_grouping(self):
        """Test complete workflow with author grouping."""
        cmd = GenerateTimeToMarketReportCommand(group_by="author")
        
        # This would be a more complex integration test
        # that tests the full workflow with real database interactions
        # For now, we'll test the structure
        assert cmd.group_by == "author"

    def test_full_workflow_team_grouping(self):
        """Test complete workflow with team grouping."""
        cmd = GenerateTimeToMarketReportCommand(group_by="team")
        
        # This would be a more complex integration test
        # that tests the full workflow with real database interactions
        # For now, we'll test the structure
        assert cmd.group_by == "team"
