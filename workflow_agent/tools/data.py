"""
Data processing tool for ETL and transformation operations.
"""

import json
from typing import Any, Optional
from datetime import datetime
from enum import Enum

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class TransformType(str, Enum):
    """Types of data transformations."""

    FILTER = "filter"
    AGGREGATE = "aggregate"
    SORT = "sort"
    MERGE = "merge"
    VALIDATE = "validate"
    NORMALIZE = "normalize"


class DataInput(BaseModel):
    """Input schema for data operations."""

    action: str = Field(
        description="Action to perform: 'transform', 'validate', 'merge', 'export', or 'analyze'"
    )
    data: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Data to process (list of records)"
    )
    transform_type: Optional[str] = Field(
        default=None,
        description="Type of transformation: filter, aggregate, sort, merge, validate, normalize",
    )
    parameters: Optional[dict[str, Any]] = Field(
        default=None, description="Parameters for the operation"
    )
    source: Optional[str] = Field(default=None, description="Data source identifier")
    output_format: Optional[str] = Field(
        default="json", description="Output format: json, csv, or dict"
    )
    batch_size: Optional[int] = Field(
        default=100, description="Batch size for processing large datasets"
    )


class DataProcessingTool(BaseTool):
    """
    Tool for data processing and transformation.

    This tool provides capabilities for:
    - Transform: Apply transformations (filter, aggregate, sort, etc.)
    - Validate: Validate data against schema/rules
    - Merge: Combine multiple datasets
    - Export: Export data in various formats
    - Analyze: Generate data analysis and statistics

    Large dataset operations are processed in batches for efficiency.
    """

    name: str = "data_processor"
    description: str = """Process and transform data efficiently.

    Actions:
    - 'transform': Apply transformations (filter, aggregate, sort, merge, validate, normalize)
    - 'validate': Validate data against rules
    - 'merge': Combine multiple datasets
    - 'export': Export data in various formats
    - 'analyze': Generate statistics and analysis

    Transform Types: filter, aggregate, sort, merge, validate, normalize
    Output Formats: json, csv, dict
    """
    args_schema: type[BaseModel] = DataInput

    sensitive_actions: list[str] = []  # Data processing is generally safe

    def _run(
        self,
        action: str,
        data: Optional[list[dict]] = None,
        transform_type: Optional[str] = None,
        parameters: Optional[dict] = None,
        source: Optional[str] = None,
        output_format: Optional[str] = "json",
        batch_size: Optional[int] = 100,
    ) -> str:
        """Synchronous run method."""
        import asyncio

        return asyncio.run(
            self._arun(action, data, transform_type, parameters, source, output_format, batch_size)
        )

    async def _arun(
        self,
        action: str,
        data: Optional[list[dict]] = None,
        transform_type: Optional[str] = None,
        parameters: Optional[dict] = None,
        source: Optional[str] = None,
        output_format: Optional[str] = "json",
        batch_size: Optional[int] = 100,
        **kwargs,
    ) -> str:
        """Asynchronous run method."""

        if action == "transform":
            return await self._transform_data(data, transform_type, parameters, output_format)
        elif action == "validate":
            return await self._validate_data(data, parameters)
        elif action == "merge":
            return await self._merge_data(data, parameters)
        elif action == "export":
            return await self._export_data(data, output_format, source)
        elif action == "analyze":
            return await self._analyze_data(data)
        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})

    async def _transform_data(
        self,
        data: Optional[list[dict]],
        transform_type: Optional[str],
        parameters: Optional[dict],
        output_format: Optional[str],
    ) -> str:
        """Apply transformation to data."""
        if not data:
            return json.dumps({"success": False, "error": "No data provided for transformation"})

        if not transform_type:
            return json.dumps({"success": False, "error": "Transform type is required"})

        original_count = len(data)

        try:
            result: list[dict[str, Any]] | dict[str, Any]
            if transform_type == "filter":
                result = self._filter_data(data, parameters or {})
            elif transform_type == "aggregate":
                result = self._aggregate_data(data, parameters or {})
            elif transform_type == "sort":
                result = self._sort_data(data, parameters or {})
            elif transform_type == "normalize":
                result = self._normalize_data(data, parameters or {})
            else:
                return json.dumps(
                    {"success": False, "error": f"Unknown transform type: {transform_type}"}
                )

            return json.dumps(
                {
                    "success": True,
                    "action": "transform",
                    "result": {
                        "transform_type": transform_type,
                        "original_count": original_count,
                        "result_count": len(result) if isinstance(result, list) else 1,
                        "data": result,
                        "output_format": output_format,
                    },
                },
                indent=2,
            )

        except Exception as e:
            return json.dumps({"success": False, "error": f"Transformation failed: {str(e)}"})

    async def _validate_data(
        self,
        data: Optional[list[dict]],
        parameters: Optional[dict],
    ) -> str:
        """Validate data against rules."""
        if not data:
            return json.dumps({"success": False, "error": "No data provided for validation"})

        errors = []
        warnings = []

        for i, record in enumerate(data):
            # Check required fields
            required_fields = parameters.get("required_fields", []) if parameters else []
            for field in required_fields:
                if field not in record or record[field] is None:
                    errors.append(f"Record {i}: Missing required field '{field}'")

            # Check field types
            field_types = parameters.get("field_types", {}) if parameters else {}
            for field, expected_type in field_types.items():
                if field in record and record[field] is not None:
                    actual_type = type(record[field]).__name__
                    if actual_type != expected_type:
                        warnings.append(
                            f"Record {i}: Field '{field}' has type {actual_type}, expected {expected_type}"
                        )

        validation_passed = len(errors) == 0

        return json.dumps(
            {
                "success": True,
                "action": "validate",
                "result": {
                    "passed": validation_passed,
                    "total_records": len(data),
                    "errors_count": len(errors),
                    "warnings_count": len(warnings),
                    "errors": errors[:10],  # Limit output
                    "warnings": warnings[:10],
                },
            },
            indent=2,
        )

    async def _merge_data(
        self,
        data: Optional[list[dict]],
        parameters: Optional[dict],
    ) -> str:
        """Merge multiple datasets."""
        if not data:
            return json.dumps({"success": False, "error": "No data provided for merging"})

        merge_key = parameters.get("key", "id") if parameters else "id"
        merge_strategy = parameters.get("strategy", "append") if parameters else "append"

        if merge_strategy == "append":
            # Simple append
            result = data
        elif merge_strategy == "dedupe":
            # Deduplicate based on key
            seen = set()
            result = []
            for record in data:
                key_value = record.get(merge_key)
                if key_value and key_value not in seen:
                    seen.add(key_value)
                    result.append(record)
        else:
            result = data

        return json.dumps(
            {
                "success": True,
                "action": "merge",
                "result": {
                    "merge_strategy": merge_strategy,
                    "merge_key": merge_key,
                    "total_records": len(result),
                    "data": result[:100],  # Limit output
                },
            },
            indent=2,
        )

    async def _export_data(
        self,
        data: Optional[list[dict]],
        output_format: Optional[str],
        source: Optional[str],
    ) -> str:
        """Export data in specified format."""
        if not data:
            return json.dumps({"success": False, "error": "No data provided for export"})

        export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if output_format == "csv":
            # Generate CSV representation
            if data:
                headers = list(data[0].keys())
                csv_lines = [",".join(headers)]
                for record in data[:100]:  # Limit for demo
                    values = [str(record.get(h, "")) for h in headers]
                    csv_lines.append(",".join(values))
                exported = "\n".join(csv_lines)
            else:
                exported = ""
        elif output_format == "json":
            exported = json.dumps(data, indent=2)
        else:
            exported = str(data)

        return json.dumps(
            {
                "success": True,
                "action": "export",
                "result": {
                    "export_id": export_id,
                    "format": output_format,
                    "source": source,
                    "record_count": len(data),
                    "preview": exported[:500] + "..." if len(exported) > 500 else exported,
                },
            },
            indent=2,
        )

    async def _analyze_data(
        self,
        data: Optional[list[dict]],
    ) -> str:
        """Analyze data and generate statistics."""
        if not data:
            return json.dumps({"success": False, "error": "No data provided for analysis"})

        # Calculate basic statistics
        total_records = len(data)

        # Field analysis
        fields: set[str] = set()
        for record in data:
            fields.update(record.keys())

        field_stats: dict[str, dict[str, Any]] = {}
        for field in fields:
            values = [r.get(field) for r in data if field in r]
            non_null = [v for v in values if v is not None]

            field_stats[field] = {
                "count": len(values),
                "non_null_count": len(non_null),
                "null_count": len(values) - len(non_null),
                "unique_values": len(set(str(v) for v in non_null)),
            }

            # Type inference
            if non_null:
                types = set(type(v).__name__ for v in non_null)
                field_stats[field]["inferred_type"] = list(types)[0] if len(types) == 1 else "mixed"

        return json.dumps(
            {
                "success": True,
                "action": "analyze",
                "result": {
                    "total_records": total_records,
                    "total_fields": len(fields),
                    "fields": list(fields),
                    "field_statistics": field_stats,
                    "data_quality": {
                        "completeness": (
                            sum(s["non_null_count"] for s in field_stats.values())
                            / (total_records * len(fields))
                            if fields
                            else 0
                        ),
                    },
                },
            },
            indent=2,
        )

    def _filter_data(self, data: list[dict], parameters: dict) -> list[dict]:
        """Filter data based on conditions."""
        conditions = parameters.get("conditions", [])

        if not conditions:
            return data

        result = []
        for record in data:
            matches = True
            for condition in conditions:
                field = condition.get("field")
                operator = condition.get("operator", "eq")
                value = condition.get("value")

                record_value = record.get(field)

                if operator == "eq" and record_value != value:
                    matches = False
                elif operator == "ne" and record_value == value:
                    matches = False
                elif operator == "gt" and record_value <= value:
                    matches = False
                elif operator == "lt" and record_value >= value:
                    matches = False
                elif operator == "contains" and value not in str(record_value):
                    matches = False

            if matches:
                result.append(record)

        return result

    def _aggregate_data(self, data: list[dict], parameters: dict) -> dict:
        """Aggregate data based on grouping."""
        group_by = parameters.get("group_by")
        aggregations = parameters.get("aggregations", ["count"])

        if not group_by:
            # Global aggregation
            return {
                "count": len(data),
                "aggregations": aggregations,
            }

        # Group data
        groups: dict[Any, list[dict[str, Any]]] = {}
        for record in data:
            key = record.get(group_by, "null")
            if key not in groups:
                groups[key] = []
            groups[key].append(record)

        # Aggregate each group
        result = {}
        for key, records in groups.items():
            result[key] = {"count": len(records)}

        return result

    def _sort_data(self, data: list[dict], parameters: dict) -> list[dict]:
        """Sort data by specified field."""
        sort_by = parameters.get("sort_by")
        reverse = parameters.get("reverse", False)

        if not sort_by:
            return data

        return sorted(
            data, key=lambda x: (x.get(sort_by) is None, x.get(sort_by, "")), reverse=reverse
        )

    def _normalize_data(self, data: list[dict], parameters: dict) -> list[dict]:
        """Normalize data fields."""
        result = []
        field_mapping = parameters.get("field_mapping", {})
        default_values = parameters.get("default_values", {})

        for record in data:
            normalized = {}

            # Apply field mapping
            for old_field, new_field in field_mapping.items():
                if old_field in record:
                    normalized[new_field] = record[old_field]

            # Copy unmapped fields
            for key, value in record.items():
                if key not in field_mapping and key not in normalized:
                    normalized[key] = value

            # Apply defaults
            for field, default in default_values.items():
                if field not in normalized or normalized[field] is None:
                    normalized[field] = default

            result.append(normalized)

        return result
