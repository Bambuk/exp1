"""Table renderer for Time To Market report."""

import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from typing import Optional
from radiator.core.logging import logger
from radiator.commands.models.time_to_market_models import TimeToMarketReport, ReportType
from radiator.commands.renderers.base_renderer import BaseRenderer


class TableRenderer(BaseRenderer):
    """Table renderer for Time To Market report."""
    
    def render(self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH) -> str:
        """
        Render report to table image file.
        
        Args:
            filepath: Output file path (optional)
            report_type: Type of report to render
            
        Returns:
            Path to generated table file
        """
        try:
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if report_type == ReportType.TTD:
                    filepath = f"reports/time_to_delivery_table_{timestamp}.png"
                elif report_type == ReportType.TTM:
                    filepath = f"reports/time_to_market_table_{timestamp}.png"
                else:
                    filepath = f"reports/time_to_market_table_{timestamp}.png"
            
            # Ensure reports directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            quarters = self._get_quarters()
            all_groups = self._get_all_groups()
            
            if not all_groups:
                logger.warning("No data to display in table")
                return ""
            
            # Create table - optimized for smaller file size
            fig_width = max(12, len(quarters) * 1.8 + 2)
            # Limit height for very large datasets to prevent extremely tall images
            max_height = 20
            fig_height = min(max_height, max(6, len(all_groups) * 0.15 + 2))
            
            # Adjust height based on report type
            if report_type == ReportType.BOTH:
                fig_height = min(max_height, max(8, len(all_groups) * 0.2 + 4))
            
            fig = plt.figure(figsize=(fig_width, fig_height))
            
            # Determine which sections to show
            show_ttd = report_type in [ReportType.TTD, ReportType.BOTH]
            show_ttm = report_type in [ReportType.TTM, ReportType.BOTH]
            
            # TTD section
            if show_ttd:
                if report_type == ReportType.BOTH:
                    ax1 = fig.add_axes([0.05, 0.55, 0.9, 0.4])
                else:
                    ax1 = fig.add_axes([0.05, 0.1, 0.9, 0.8])
                ax1.axis('off')
                self._render_ttd_table(ax1, quarters, all_groups)
            
            # TTM section
            if show_ttm:
                if report_type == ReportType.BOTH:
                    ax2 = fig.add_axes([0.05, 0.05, 0.9, 0.4])
                else:
                    ax2 = fig.add_axes([0.05, 0.1, 0.9, 0.8])
                ax2.axis('off')
                self._render_ttm_table(ax2, quarters, all_groups)
            
            # Main title
            title = self._get_title(report_type)
            fig.suptitle(title, fontsize=12, fontweight='bold', y=0.95)
            
            # Save with optimized settings for smaller file size
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', 
                       pad_inches=0.1, edgecolor='none', transparent=False)
            plt.close()
            
            logger.info(f"Table saved to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate table: {e}")
            raise
    
    def _render_ttd_table(self, ax, quarters: list, all_groups: list):
        """Render TTD table section."""
        # Prepare data with proper structure
        ttd_table_data = []
        for group in all_groups:
            row = [group]
            for quarter in quarters:
                quarter_report = self.report.quarter_reports.get(quarter)
                group_metrics = quarter_report.groups.get(group) if quarter_report else None
                if group_metrics:
                    ttd_avg = group_metrics.ttd_metrics.mean or 0
                    ttd_p85 = group_metrics.ttd_metrics.p85 or 0
                    tasks = group_metrics.ttd_metrics.count
                    row.extend([f"{ttd_avg:.1f}", f"{ttd_p85:.1f}", str(tasks)])
                else:
                    row.extend(["", "", ""])
            ttd_table_data.append(row)
        
        # Create headers
        ttd_headers = ['Group']
        for quarter in quarters:
            ttd_headers.extend([f'{quarter}\nAvg', f'{quarter}\n85%', f'{quarter}\nTasks'])
        
        # Create table
        ttd_table = ax.table(cellText=ttd_table_data,
                             colLabels=ttd_headers,
                             cellLoc='center',
                             loc='center',
                             colWidths=[0.15] + [0.28/len(quarters)] * (len(quarters) * 3))
        
        # Style TTD table
        self._style_table(ttd_table, len(ttd_headers), len(ttd_table_data), all_groups, '#4CAF50')
        ax.set_title('Time To Delivery (days)', fontsize=12, fontweight='bold', pad=10)
    
    def _render_ttm_table(self, ax, quarters: list, all_groups: list):
        """Render TTM table section."""
        # Prepare data with proper structure
        ttm_table_data = []
        for group in all_groups:
            row = [group]
            for quarter in quarters:
                quarter_report = self.report.quarter_reports.get(quarter)
                group_metrics = quarter_report.groups.get(group) if quarter_report else None
                if group_metrics:
                    ttm_avg = group_metrics.ttm_metrics.mean or 0
                    ttm_p85 = group_metrics.ttm_metrics.p85 or 0
                    tasks = group_metrics.ttm_metrics.count
                    row.extend([f"{ttm_avg:.1f}", f"{ttm_p85:.1f}", str(tasks)])
                else:
                    row.extend(["", "", ""])
            ttm_table_data.append(row)
        
        # Create headers
        ttm_headers = ['Group']
        for quarter in quarters:
            ttm_headers.extend([f'{quarter}\nAvg', f'{quarter}\n85%', f'{quarter}\nTasks'])
        
        # Create table
        ttm_table = ax.table(cellText=ttm_table_data,
                             colLabels=ttm_headers,
                             cellLoc='center',
                             loc='center',
                             colWidths=[0.15] + [0.28/len(quarters)] * (len(quarters) * 3))
        
        # Style TTM table
        self._style_table(ttm_table, len(ttm_headers), len(ttm_table_data), all_groups, '#2196F3')
        ax.set_title('Time To Market (days)', fontsize=12, fontweight='bold', pad=10)
    
    def _style_table(self, table, num_headers: int, num_rows: int, all_groups: list, header_color: str):
        """Style table with colors and formatting."""
        table.auto_set_font_size(False)
        # Use smaller font for large datasets
        font_size = 5 if len(all_groups) > 30 else 6
        table.set_fontsize(font_size)
        # Reduce scaling for large datasets
        scale_y = 0.8 if len(all_groups) > 30 else 1.2
        table.scale(1.0, scale_y)
        
        # Style header row
        for i in range(num_headers):
            table[(0, i)].set_facecolor(header_color)
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Style data rows
        for i in range(1, num_rows + 1):
            for j in range(num_headers):
                cell = table[(i, j)]
                if i % 2 == 0:
                    cell.set_facecolor('#F5F5F5')
                else:
                    cell.set_facecolor('#FFFFFF')
                
                if j == 0:  # Group column
                    cell.set_text_props(ha='left', va='center')
                else:  # Data columns
                    cell.set_text_props(ha='center', va='center')
    
    def _get_title(self, report_type: ReportType) -> str:
        """Get title for the report."""
        group_name = self.report.group_by.value.title()
        
        if report_type == ReportType.TTD:
            return f'Time To Delivery Report - {group_name} Grouping'
        elif report_type == ReportType.TTM:
            return f'Time To Market Report - {group_name} Grouping'
        else:
            return f'Time To Delivery & Time To Market Report - {group_name} Grouping'
