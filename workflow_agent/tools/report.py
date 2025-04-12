"""
Report generation tool for creating various types of reports.
"""

import json
from typing import Any, Optional
from datetime import datetime
from enum import Enum

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Types of reports that can be generated."""

    SUMMARY = "summary"
    DETAILED = "detailed"
    METRICS = "metrics"
    COMPARISON = "comparison"
    TREND = "trend"


class ReportInput(BaseModel):
    """Input schema for report generation."""

    action: str = Field(
        description="Action to perform: 'generate', 'schedule', 'list_templates', or 'preview'"
    )
    report_type: Optional[str] = Field(
        default="summary",
        description="Type of report: summary, detailed, metrics, comparison, trend",
    )
    title: Optional[str] = Field(default=None, description="Report title")
    data: Optional[dict[str, Any]] = Field(
        default=None, description="Data to include in the report"
    )
    data_source: Optional[str] = Field(default=None, description="Source identifier for the data")
    format: Optional[str] = Field(
        default="markdown", description="Output format: markdown, html, json, or text"
    )
    parameters: Optional[dict[str, Any]] = Field(
        default=None, description="Additional parameters for report generation"
    )
    include_summary: Optional[bool] = Field(
        default=True, description="Whether to include an executive summary"
    )


class ReportGeneratorTool(BaseTool):
    """
    Tool for generating various types of reports.

    This tool provides capabilities for:
    - Generate: Create a new report from data
    - Schedule: Schedule a recurring report (requires approval)
    - List Templates: Get available report templates
    - Preview: Generate a preview of a report

    Reports can be generated in multiple formats and can include
    summaries, charts, and visualizations.
    """

    name: str = "report_generator"
    description: str = """Generate professional reports from data.

    Actions:
    - 'generate': Create a new report from provided data
    - 'schedule': Set up a recurring report (REQUIRES APPROVAL)
    - 'list_templates': Get available report templates
    - 'preview': Generate a quick preview of a report

    Formats: markdown, html, json, text

    Sensitive Actions (require approval): schedule
    """
    args_schema: type[BaseModel] = ReportInput

    sensitive_actions: list[str] = ["schedule"]

    def _run(
        self,
        action: str,
        report_type: Optional[str] = "summary",
        title: Optional[str] = None,
        data: Optional[dict] = None,
        data_source: Optional[str] = None,
        format: Optional[str] = "markdown",
        parameters: Optional[dict] = None,
        include_summary: Optional[bool] = True,
    ) -> str:
        """Synchronous run method."""
        import asyncio

        return asyncio.run(
            self._arun(
                action, report_type, title, data, data_source, format, parameters, include_summary
            )
        )

    async def _arun(
        self,
        action: str,
        report_type: Optional[str] = "summary",
        title: Optional[str] = None,
        data: Optional[dict] = None,
        data_source: Optional[str] = None,
        format: Optional[str] = "markdown",
        parameters: Optional[dict] = None,
        include_summary: Optional[bool] = True,
    ) -> str:
        """Asynchronous run method."""

        if action == "generate":
            return await self._generate_report(
                report_type, title, data, data_source, format, parameters, include_summary
            )
        elif action == "schedule":
            return await self._schedule_report(report_type, title, data_source, format, parameters)
        elif action == "list_templates":
            return await self._list_templates()
        elif action == "preview":
            return await self._preview_report(report_type, data, format)
        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})

    async def _generate_report(
        self,
        report_type: Optional[str],
        title: Optional[str],
        data: Optional[dict],
        data_source: Optional[str],
        format: Optional[str],
        parameters: Optional[dict],
        include_summary: Optional[bool],
    ) -> str:
        """Generate a complete report."""
        if not data and not data_source:
            return json.dumps(
                {"success": False, "error": "Either 'data' or 'data_source' must be provided"}
            )

        resolved_report_type = report_type or ReportType.SUMMARY.value
        resolved_format = format or "markdown"
        summary_enabled = True if include_summary is None else include_summary
        report_id = f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_title = (
            title
            or f"{resolved_report_type.title()} Report - {datetime.now().strftime('%Y-%m-%d')}"
        )

        # Process data based on report type
        processed_data = self._process_data(resolved_report_type, data or {})

        # Generate content based on format
        if resolved_format == "markdown":
            content = self._generate_markdown(report_title, processed_data, summary_enabled)
        elif resolved_format == "html":
            content = self._generate_html(report_title, processed_data, summary_enabled)
        elif resolved_format == "json":
            content = json.dumps(processed_data, indent=2)
        else:
            content = self._generate_text(report_title, processed_data, summary_enabled)

        return json.dumps(
            {
                "success": True,
                "action": "generate",
                "result": {
                    "report_id": report_id,
                    "title": report_title,
                    "type": resolved_report_type,
                    "format": resolved_format,
                    "content": content,
                    "generated_at": datetime.now().isoformat(),
                    "metadata": {
                        "data_source": data_source,
                        "parameters": parameters,
                        "include_summary": summary_enabled,
                    },
                },
            },
            indent=2,
        )

    async def _schedule_report(
        self,
        report_type: Optional[str],
        title: Optional[str],
        data_source: Optional[str],
        format: Optional[str],
        parameters: Optional[dict],
    ) -> str:
        """Schedule a recurring report (requires approval)."""
        schedule_id = f"sched_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return json.dumps(
            {
                "success": True,
                "action": "schedule",
                "requires_approval": True,
                "result": {
                    "schedule_id": schedule_id,
                    "report_type": report_type,
                    "title": title or f"Scheduled {report_type} Report",
                    "data_source": data_source,
                    "format": format,
                    "schedule": parameters.get("schedule", "weekly") if parameters else "weekly",
                    "created_at": datetime.now().isoformat(),
                },
                "message": "Report scheduled pending approval",
            },
            indent=2,
        )

    async def _list_templates(self) -> str:
        """List available report templates."""
        templates = [
            {
                "id": "summary",
                "name": "Summary Report",
                "description": "High-level overview with key metrics",
                "default_format": "markdown",
            },
            {
                "id": "detailed",
                "name": "Detailed Report",
                "description": "Comprehensive report with all data",
                "default_format": "html",
            },
            {
                "id": "metrics",
                "name": "Metrics Dashboard",
                "description": "KPI-focused report with visualizations",
                "default_format": "html",
            },
            {
                "id": "comparison",
                "name": "Comparison Report",
                "description": "Period-over-period comparison",
                "default_format": "markdown",
            },
            {
                "id": "trend",
                "name": "Trend Analysis",
                "description": "Historical trends and projections",
                "default_format": "html",
            },
        ]

        return json.dumps(
            {
                "success": True,
                "action": "list_templates",
                "result": {"templates": templates, "total": len(templates)},
            },
            indent=2,
        )

    async def _preview_report(
        self,
        report_type: Optional[str],
        data: Optional[dict],
        format: Optional[str],
    ) -> str:
        """Generate a quick preview of a report."""
        resolved_report_type = report_type or ReportType.SUMMARY.value
        resolved_format = format or "markdown"
        preview_data = data or {"sample": "preview data"}

        return json.dumps(
            {
                "success": True,
                "action": "preview",
                "result": {
                    "type": resolved_report_type,
                    "format": resolved_format,
                    "preview": f"Preview of {resolved_report_type} report...",
                    "sample_output": self._generate_markdown(
                        "Preview Report",
                        self._process_data(resolved_report_type, preview_data),
                        True,
                    )[:500]
                    + "...",
                },
            },
            indent=2,
        )

    def _process_data(self, report_type: str, data: dict) -> dict:
        """Process data based on report type."""
        processed = {
            "raw_data": data,
            "type": report_type,
        }

        if report_type == "summary":
            processed["summary_stats"] = self._calculate_summary_stats(data)
        elif report_type == "metrics":
            processed["metrics"] = self._extract_metrics(data)
        elif report_type == "comparison":
            processed["comparison"] = self._generate_comparison(data)
        elif report_type == "trend":
            processed["trends"] = self._analyze_trends(data)

        return processed

    def _calculate_summary_stats(self, data: dict) -> dict:
        """Calculate summary statistics from data."""
        return {
            "total_records": len(data) if isinstance(data, (list, dict)) else 0,
            "generated_at": datetime.now().isoformat(),
            "data_points": sum(1 for _ in str(data)),
        }

    def _extract_metrics(self, data: dict) -> dict:
        """Extract key metrics from data."""
        return {
            "primary_metrics": [],
            "secondary_metrics": [],
            "data_quality_score": 0.95,
        }

    def _generate_comparison(self, data: dict) -> dict:
        """Generate comparison data."""
        return {
            "period_a": {"start": "Previous Period", "data": {}},
            "period_b": {"start": "Current Period", "data": data},
            "changes": [],
        }

    def _analyze_trends(self, data: dict) -> dict:
        """Analyze trends in data."""
        return {
            "direction": "stable",
            "confidence": 0.85,
            "projections": [],
        }

    def _generate_markdown(self, title: str, data: dict, include_summary: bool) -> str:
        """Generate markdown formatted report."""
        lines = [
            f"# {title}",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
        ]

        if include_summary:
            lines.extend(
                [
                    "## Executive Summary",
                    "",
                    "This report provides an overview of the analyzed data.",
                    "",
                ]
            )

        lines.extend(
            [
                "## Data Overview",
                "",
                "```json",
                json.dumps(data.get("raw_data", data), indent=2)[:1000],
                "```",
                "",
            ]
        )

        return "\n".join(lines)

    def _generate_html(self, title: str, data: dict, include_summary: bool) -> str:
        """Generate HTML formatted report."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .data {{ margin-top: 20px; }}
        .generated {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="generated">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        if include_summary:
            html += """
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>This report provides an overview of the analyzed data.</p>
    </div>
"""
        html += """
    <div class="data">
        <h2>Data Overview</h2>
        <pre>Data visualization would appear here</pre>
    </div>
</body>
</html>"""
        return html

    def _generate_text(self, title: str, data: dict, include_summary: bool) -> str:
        """Generate plain text report."""
        lines = [
            f"{'=' * len(title)}",
            title,
            f"{'=' * len(title)}",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        if include_summary:
            lines.extend(
                [
                    "EXECUTIVE SUMMARY",
                    "-" * 16,
                    "This report provides an overview of the analyzed data.",
                    "",
                ]
            )

        lines.extend(
            [
                "DATA OVERVIEW",
                "-" * 12,
                "See attached data for details.",
                "",
            ]
        )

        return "\n".join(lines)
