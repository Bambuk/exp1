"""Simple test for pause time functionality."""

import pytest
from datetime import datetime

from radiator.commands.services.metrics_service import MetricsService
from radiator.commands.models.time_to_market_models import StatusHistoryEntry


class TestPauseTimeSimple:
    """Simple tests for pause time functionality."""
    
    def test_pause_time_calculation_and_exclusion(self):
        """Test that pause time is calculated and excluded from TTM/TTD."""
        service = MetricsService()
        
        # Create history with pause time
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 3), None),
            StatusHistoryEntry("Приостановлено", "Приостановлено", datetime(2024, 1, 5), None),
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 8), None),
            StatusHistoryEntry("Готова к разработке", "Готова к разработке", datetime(2024, 1, 10), None),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 12), None),
        ]
        
        # Calculate pause time
        pause_time = service.calculate_pause_time(history)
        assert pause_time == 3  # 8-5 = 3 days in pause
        
        # Calculate TTD (should exclude pause time)
        ttd = service.calculate_time_to_delivery(history, ["Discovery"])
        assert ttd == 4  # 10-3=7 days total, minus 3 days pause = 4 days
        
        # Calculate TTM (should exclude pause time)
        ttm = service.calculate_time_to_market(history, ["Done"])
        assert ttm == 6  # 12-3=9 days total, minus 3 days pause = 6 days
    
    def test_enhanced_statistics_with_pause_time(self):
        """Test enhanced statistics calculation with pause time."""
        service = MetricsService()
        
        times = [1, 2, 3]
        pause_times = [0, 1, 2]
        
        result = service.calculate_enhanced_statistics(times, pause_times)
        
        assert result.times == times
        assert result.mean == 2.0
        assert result.p85 == 2.7
        assert result.count == 3
        assert result.pause_times == pause_times
        assert result.pause_mean == 1.0
        assert result.pause_p85 == 1.7
    
    def test_no_pause_time(self):
        """Test behavior when no pause time exists."""
        service = MetricsService()
        
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 3), None),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 5), None),
        ]
        
        # Calculate pause time
        pause_time = service.calculate_pause_time(history)
        assert pause_time == 0
        
        # Calculate TTM (should be normal)
        ttm = service.calculate_time_to_market(history, ["Done"])
        assert ttm == 2  # 5-3 = 2 days, no pause time


if __name__ == "__main__":
    pytest.main([__file__])
