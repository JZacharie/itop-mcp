#!/usr/bin/env python3
"""
iTop MCP Server

A Model Context Protocol server for interacting with iTop ITSM system via REST API.
Provides tools for managing tickets, CIs, and other iTop objects.
"""

import json
import os
import re
from typing import Any, Optional, Union

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("itop-mcp", description="iTop ITSM integration server")

# Configuration
ITOP_BASE_URL = os.getenv("ITOP_BASE_URL", "")
ITOP_USER = os.getenv("ITOP_USER", "")
ITOP_PASSWORD = os.getenv("ITOP_PASSWORD", "")
ITOP_VERSION = os.getenv("ITOP_VERSION", "1.4")


class ITopClient:
    """Client for interacting with iTop REST API"""
    
    def __init__(self, base_url: str, username: str, password: str, version: str = "1.4"):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.version = version
        self.rest_url = f"{self.base_url}/webservices/rest.php"
    
    async def make_request(self, operation_data: dict) -> dict:
        """Make a REST request to iTop"""
        headers = {
            "User-Agent": "iTop-MCP-Server/1.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "version": self.version,
            "auth_user": self.username,
            "auth_pwd": self.password,
            "json_data": json.dumps(operation_data)
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.rest_url, data=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                raise ConnectionError(f"Request failed: {e}") from e
            except httpx.HTTPStatusError as e:
                raise ValueError(f"HTTP error {e.response.status_code}: {e.response.text}") from e
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response: {e}") from e


# Initialize iTop client
def get_itop_client() -> ITopClient:
    """Get configured iTop client"""
    if not all([ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD]):
        raise ValueError("Missing required environment variables: ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD")
    return ITopClient(ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD, ITOP_VERSION)


@mcp.tool()
async def list_operations() -> str:
    """List all available operations in the iTop REST API."""
    try:
        client = get_itop_client()
        operation_data = {"operation": "list_operations"}
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        operations = result.get("operations", [])
        output = "Available iTop REST API operations:\n\n"
        
        for op in operations:
            output += f"• {op.get('verb', 'Unknown')}: {op.get('description', 'No description')}\n"
        
        return output
    except Exception as e:
        return f"Error listing operations: {str(e)}"


@mcp.tool()
async def get_objects(
    class_name: str, 
    key: Optional[str] = None, 
    output_fields: str = "*", 
    limit: int = 20,
    format_output: str = "detailed"
) -> str:
    """
    Get objects from iTop with optimized performance and flexible output formatting.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Person, Organization)
        key: Optional search criteria. Can be an ID, OQL query, or JSON search criteria
        output_fields: Comma-separated list of fields to return, or "*" for all fields
        limit: Maximum number of objects to return (default: 20, max: 100)
        format_output: Output format - "detailed", "summary", "table", or "json" (default: detailed)
    """
    try:
        # Validate inputs
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
            
        valid_formats = ["detailed", "summary", "table", "json"]
        if format_output not in valid_formats:
            format_output = "detailed"
        
        client = get_itop_client()
        
        # Build operation data more efficiently
        operation_data = {
            "operation": "core/get",
            "class": class_name,
            "output_fields": output_fields,
            "limit": limit
        }
        
        # Optimized key handling with better validation
        if key:
            key = key.strip()
            if key.upper().startswith("SELECT"):
                # OQL query - validate basic syntax
                if not key.upper().startswith(f"SELECT {class_name.upper()}"):
                    key = f"SELECT {class_name} WHERE {key[6:].strip()}" if key.upper().startswith("SELECT") else key
                operation_data["key"] = key
            elif key.isdigit():
                # Numeric ID
                operation_data["key"] = int(key)
            elif key.startswith("{") and key.endswith("}"):
                # JSON search criteria
                try:
                    parsed_key = json.loads(key)
                    operation_data["key"] = parsed_key
                except json.JSONDecodeError as e:
                    return f"Error: Invalid JSON in key parameter: {e}"
            else:
                # String ID or simple search - try as ID first, then as search
                operation_data["key"] = key
        else:
            # If no key provided, select all objects of the class
            operation_data["key"] = f"SELECT {class_name}"
        
        # Make the request
        result = await client.make_request(operation_data)
        
        # Handle API errors
        if result.get("code") != 0:
            error_msg = result.get("message", "Unknown error")
            return f"Error: {error_msg}"
        
        objects = result.get("objects")
        if not objects:
            search_info = f" matching criteria '{key}'" if key else ""
            return f"No {class_name} objects found{search_info}."
        
        # Format output based on requested format
        return _format_objects_output(objects, class_name, format_output, key)
        
    except Exception as e:
        return f"Error getting objects: {str(e)}"


def _format_field_value(value: Any, max_length: int = 500) -> str:
    """Helper function to format field values for display with NO truncation."""
    if value is None:
        return "None"
    str_value = str(value)
    # Handle HTML content
    if "<" in str_value and ">" in str_value:
        str_value = re.sub(r'<[^>]+>', '', str_value).strip()
    # Do NOT truncate values
    str_value = str_value.replace("\n", " ").replace("\r", "")
    return str_value


def _format_field_value(value: Any, max_length: int = 500) -> str:
    """Helper function to format field values for display with NO truncation."""
    if value is None:
        return "None"
    str_value = str(value)
    # Handle HTML content
    if "<" in str_value and ">" in str_value:
        str_value = re.sub(r'<[^>]+>', '', str_value).strip()
    # Do NOT truncate values
    str_value = str_value.replace("\n", " ").replace("\r", "")
    return str_value


def _format_objects_output(objects: dict, class_name: str, format_type: str, search_key: Optional[str] = None) -> str:
    """Helper function to format object output in different styles (no field count/length limits)."""
    
    if format_type == "json":
        # Return clean JSON format
        clean_objects = {}
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                clean_objects[obj_key] = obj_data.get("fields", {})
        return json.dumps(clean_objects, indent=2, default=str)
    
    # Prepare header
    search_info = f" matching '{search_key}'" if search_key else ""
    header = f"Found {len(objects)} {class_name} object(s){search_info}:\n\n"
    
    if format_type == "summary":
        # Summary format - show ALL non-empty fields for each object
        output = header
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                # Show all non-empty fields
                field_values = [f"{field_name}: {_format_field_value(field_value)}" for field_name, field_value in fields.items() if field_value]
                output += f"🔹 **{obj_key}** - {', '.join(field_values)}\n"
                # Show all non-empty fields
                field_values = [f"{field_name}: {_format_field_value(field_value)}" for field_name, field_value in fields.items() if field_value]
                output += f"🔹 **{obj_key}** - {', '.join(field_values)}\n"
        return output

    elif format_type == "table":
        # Table format - show ALL fields present in any object
        output = header
        
        # Collect all fields across all objects (not just non-empty)
        all_fields = set()
        valid_objects = []
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                all_fields.update(fields.keys())
                valid_objects.append((obj_key, fields))
        
        if not all_fields:
            return output + "No fields found for table display."
        
        # Sort fields for consistent column order
        display_fields = sorted(list(all_fields))
        col_widths = {field: max(len(field), 15) for field in display_fields}
        col_widths["key"] = max(len("Object Key"), max(len(obj_key) for obj_key, _ in valid_objects) if valid_objects else 10)
        
        # Header row
        header_row = f"{'Object Key':<{col_widths['key']}} | "
        header_row += " | ".join(f"{field:<{col_widths[field]}}" for field in all_fields)
        output += header_row + "\n"
        output += "-" * len(header_row) + "\n"
        
        # Data rows
        for obj_key, fields in valid_objects:
            row = f"{obj_key:<{col_widths['key']}} | "
            row_values = []
            for field in display_fields:
                value = _format_field_value(fields.get(field, ""))
                row_values.append(f"{value:<{col_widths[field]}}")
            row += " | ".join(row_values)
            output += row + "\n"
        
        return output
    
    else:  # detailed format (default)
        output = header
        
        # Group important fields for better organization
        priority_fields = ["id", "friendlyname", "name", "title", "status", "ref"]
        secondary_fields = ["creation_date", "last_update", "caller_name", "agent_name", "org_name", "description"]
        
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                output += f"🔹 **{obj_key}**\n"
                
                # Show priority fields first
                for field in priority_fields:
                    if field in fields and fields[field]:
                        value = _format_field_value(fields[field])
                        output += f"   {field}: {value}\n"
                
                # Show secondary fields
                has_secondary = False
                for field in secondary_fields:
                    if field in fields and fields[field] and field not in priority_fields:
                        if not has_secondary:
                            output += "   ---\n"
                            has_secondary = True
                        value = _format_field_value(fields[field])
                        output += f"   {field}: {value}\n"
                
                # Show remaining fields (collapsed)
                remaining_fields = {k: v for k, v in fields.items() 
                                   if k not in priority_fields + secondary_fields and v}
                if remaining_fields:
                    output += f"   Other fields ({len(remaining_fields)}): "
                    field_summary = ", ".join(f"{k}={str(v)[:20]}..." if len(str(v)) > 20 else f"{k}={v}" 
                                            for k, v in list(remaining_fields.items())[:3])
                    output += field_summary
                    if len(remaining_fields) > 3:
                        output += f" and {len(remaining_fields) - 3} more..."
                    output += "\n"
                
                output += "\n"
            else:
                output += f"❌ **{obj_key}**: Error - {obj_data.get('message', 'Unknown error')}\n\n"
        
        return output


def _format_objects_output_smart(objects: dict, class_name: str, format_type: str, class_fields: dict, requested_fields: list = None, search_key: Optional[str] = None) -> str:
    """
    Smart helper function to format object output using dynamically discovered fields.
    Provides rich formatting with NO field limits or value trimming.
    Offers special handling for SLA, date fields, and relationships.
    """
    
    if format_type == "json":
        # Return clean JSON format with ALL fields
        clean_objects = {}
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                clean_objects[obj_key] = obj_data.get("fields", {})
        return json.dumps(clean_objects, indent=2, default=str)
    
    # Prepare header
    search_info = f" matching '{search_key}'" if search_key else ""
    header = f"Found {len(objects)} {class_name} object(s){search_info}:\n\n"
    
    if format_type == "summary":
        # Summary format - show ALL non-empty fields for each object
        output = header
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                # Show all non-empty fields
                field_values = [f"{field_name}: {_format_field_value(field_value)}" for field_name, field_value in fields.items() if field_value]
                output += f"🔹 **{obj_key}** - {', '.join(field_values)}\n"
        return output

    elif format_type == "table":
        # Table format - show ALL fields present in any object
        output = header
        
        # Collect all fields across all objects (not just non-empty)
        all_fields = set()
        valid_objects = []
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                all_fields.update(fields.keys())
                valid_objects.append((obj_key, fields))
        
        if not all_fields:
            return output + "No fields found for table display."
        
        # Sort fields for consistent column order
        display_fields = sorted(list(all_fields))
        col_widths = {field: max(len(field), 15) for field in display_fields}
        col_widths["key"] = max(len("Object Key"), max(len(obj_key) for obj_key, _ in valid_objects) if valid_objects else 10)
        
        # Header row
        header_row = f"{'Object Key':<{col_widths['key']}} | "
        header_row += " | ".join(f"{field:<{col_widths[field]}}" for field in display_fields)
        output += header_row + "\n"
        output += "-" * len(header_row) + "\n"
        
        # Data rows
        for obj_key, fields in valid_objects:
            row = f"{obj_key:<{col_widths['key']}} | "
            row_values = []
            for field in display_fields:
                value = _format_field_value(fields.get(field, ""))
                row_values.append(f"{value:<{col_widths[field]}}")
            row += " | ".join(row_values)
            output += row + "\n"
        
        return output
    
    else:  # detailed format (default) - SHOW ALL FIELDS
        output = header
        
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                
                output += f"🔹 **{obj_key}**\n"
                
                # Show ALL fields dynamically - both populated and empty fields
                populated_fields = []
                empty_fields = []
                
                for field_name, field_value in fields.items():
                    if field_value and str(field_value).strip():  # Fields with values
                        populated_fields.append((field_name, field_value))
                    else:  # Empty or None fields
                        empty_fields.append(field_name)
                
                # First show all populated fields
                for field_name, field_value in populated_fields:
                    output += f"   **{field_name}**: {_format_field_value(field_value)}\n"
                
                # Then show empty fields in a compact format (optional detail)
                if empty_fields:
                    output += f"   *Empty fields*: {', '.join(empty_fields[:10])}"
                    if len(empty_fields) > 10:
                        output += f" (+{len(empty_fields) - 10} more)"
                    output += "\n"
                
                output += "\n"
        
        return output


async def discover_field_values(class_name: str, field_name: str, limit: int = 100) -> dict:
    """
    **UNIVERSAL FIELD VALUE DISCOVERY**
    
    Dynamically discover unique values for ANY field in ANY iTop class.
    This is the core function that enables truly schema-adaptive queries.
    
    Args:
        class_name: The iTop class to query
        field_name: The specific field to discover values for
        limit: Max number of unique values to sample (default: 100)
    
    Returns:
        dict: {
            "values": [list of unique values],
            "total_sampled": int,
            "field_type": "enum|text|numeric|date|boolean",
            "sample_pattern": "detected pattern if any"
        }
    """
    try:
        client = get_itop_client()
        
        # Get a larger sample to discover unique values
        sample_size = min(limit * 3, 500)  # Sample more to get diverse values
        
        operation_data = {
            "operation": "core/get",
            "class": class_name,
            "key": f"SELECT {class_name}",
            "output_fields": f"id,{field_name}",  # Only get ID and the field we're interested in
            "limit": sample_size
        }
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return {"values": [], "total_sampled": 0, "field_type": "unknown", "sample_pattern": ""}
        
        objects = result.get("objects", {})
        if not objects:
            return {"values": [], "total_sampled": 0, "field_type": "unknown", "sample_pattern": ""}
        
        # Extract and analyze field values
        values = []
        for obj_data in objects.values():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                value = fields.get(field_name)
                if value is not None and value != "":
                    values.append(str(value))
        
        # Get unique values (preserve order)
        unique_values = []
        seen = set()
        for value in values:
            if value not in seen:
                unique_values.append(value)
                seen.add(value)
                if len(unique_values) >= limit:
                    break
        
        # Analyze field type and patterns
        field_analysis = _analyze_field_values(unique_values, field_name)
        
        return {
            "values": unique_values,
            "total_sampled": len(values),
            "field_type": field_analysis["type"],
            "sample_pattern": field_analysis["pattern"],
            "confidence": field_analysis["confidence"]
        }
        
    except Exception as e:
        return {"values": [], "total_sampled": 0, "field_type": "unknown", "sample_pattern": "", "error": str(e)}

def _analyze_field_values(values: list, field_name: str) -> dict:
    """
    Analyze field values to determine type, patterns, and confidence.
    This helps the AI understand what kind of field it's working with.
    """
    if not values:
        return {"type": "unknown", "pattern": "", "confidence": 0}
    
    field_lower = field_name.lower()
    
    # Determine field type based on values and field name
    field_type = "text"  # default
    pattern = ""
    confidence = 0.5
    
    # Check for numeric values
    numeric_count = 0
    for value in values:
        try:
            float(value)
            numeric_count += 1
        except ValueError:
            pass
    
    if numeric_count > len(values) * 0.8:
        field_type = "numeric"
        confidence = 0.9
    
    # Check for boolean-like values
    boolean_indicators = {"yes", "no", "true", "false", "1", "0", "on", "off", "enabled", "disabled"}
    if all(value.lower() in boolean_indicators for value in values):
        field_type = "boolean"
        confidence = 0.95
    
    # Check for date patterns
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'  # YYYY-MM-DD HH:MM:SS
    ]
    
    date_matches = 0
    for value in values:
        for pattern_regex in date_patterns:
            if re.match(pattern_regex, value):
                date_matches += 1
                break
    
    if date_matches > len(values) * 0.7:
        field_type = "date"
        confidence = 0.9
    
    # Check for enumeration (limited unique values)
    if len(set(values)) <= 20 and len(values) > 10:
        field_type = "enum"
        confidence = 0.8
        pattern = f"enum({len(set(values))} unique values)"
    
    # Field name analysis for additional confidence
    if any(indicator in field_lower for indicator in ["status", "state", "type", "priority", "level"]):
        field_type = "enum"
        confidence = min(confidence + 0.2, 1.0)
    
    if any(indicator in field_lower for indicator in ["date", "time", "created", "modified", "updated"]):
        field_type = "date"
        confidence = min(confidence + 0.2, 1.0)
    
    if any(indicator in field_lower for indicator in ["id", "count", "number", "size", "amount"]):
        field_type = "numeric"
        confidence = min(confidence + 0.2, 1.0)
    
    return {
        "type": field_type,
        "pattern": pattern,
        "confidence": confidence
    }

def classify_query_complexity(query: str, query_analysis: dict) -> dict:
    """
    **QUERY INTELLIGENCE CLASSIFIER**
    
    Determines whether a query is simple (list all) or complex (needs value discovery).
    This is the key function that prevents over-processing simple queries.
    
    Returns:
        dict: {
            "complexity": "simple|moderate|complex",
            "needs_value_discovery": bool,
            "discovery_fields": [list of fields that need value discovery],
            "reasoning": "explanation of classification"
        }
    """
    query_lower = query.lower()
    
    # Simple query indicators
    simple_indicators = [
        "list all", "show all", "get all", "display all",
        "list", "show", "get", "display", "fetch",
        "what are", "give me"
    ]
    
    # Complex query indicators
    complex_indicators = [
        "where", "with", "having", "filter", "only",
        "by status", "by type", "by priority", "by organization",
        "count by", "group by", "breakdown by", "based stats", "stats",
        "running", "using", "containing", "matching",
        "more than", "less than", "greater than", "equal to",
        "in", "not in", "between", "vs", "versus", "closed", "on time"
    ]
    
    # Check for simple patterns first
    is_simple = False
    for indicator in simple_indicators:
        if indicator in query_lower:
            # Check if it's truly simple (no additional complexity)
            remaining_query = query_lower.replace(indicator, "").strip()
            if len(remaining_query.split()) <= 3:  # e.g., "list all servers"
                is_simple = True
                break
    
    # Check for complex patterns
    complexity_score = 0
    detected_complex_indicators = []
    
    for indicator in complex_indicators:
        if indicator in query_lower:
            complexity_score += 1
            detected_complex_indicators.append(indicator)
    
    # Analyze discovered filters from query analysis
    discovered_filters = query_analysis.get("discovered_filters", [])
    raw_filters = query_analysis.get("raw_filters", [])
    
    # Determine fields that need value discovery
    discovery_fields = []
    
    # From discovered filters - only for complex queries
    for filter_info in discovered_filters:
        field = filter_info.get("field")
        if field and field not in discovery_fields:
            discovery_fields.append(field)
    
    # From grouping
    if query_analysis.get("grouping"):
        grouping_field = query_analysis["grouping"]
        if grouping_field not in discovery_fields:
            discovery_fields.append(grouping_field)
    
    # From raw filters that might need field mapping
    for raw_filter in raw_filters:
        category = raw_filter.get("category")
        if category and category not in ["memory", "priority"]:  # Skip numeric categories
            discovery_fields.append(category)  # Will be mapped to actual field later
    
    # Final classification
    if is_simple and complexity_score == 0 and not discovery_fields:
        return {
            "complexity": "simple",
            "needs_value_discovery": False,
            "discovery_fields": [],
            "reasoning": f"Simple query detected: '{query}' - no filtering or grouping needed"
        }
    
    elif complexity_score <= 2 and len(discovery_fields) <= 2:
        return {
            "complexity": "moderate",
            "needs_value_discovery": True,
            "discovery_fields": discovery_fields,
            "reasoning": f"Moderate complexity: {complexity_score} indicators, {len(discovery_fields)} fields need discovery"
        }
    
    else:
        return {
            "complexity": "complex",
            "needs_value_discovery": True,
            "discovery_fields": discovery_fields,
            "reasoning": f"Complex query: {complexity_score} indicators, {len(discovery_fields)} fields need discovery"
        }

async def enhance_query_analysis_with_values(query_analysis: dict, class_name: str, class_fields: dict) -> dict:
    """
    **INTELLIGENT VALUE DISCOVERY ENHANCER**
    
    Enhances query analysis by discovering actual field values for fields that need it.
    Only runs when query complexity analysis determines it's needed.
    
    This is what makes the MCP truly intelligent - it can adapt to any field, any query.
    """
    enhanced_analysis = query_analysis.copy()
    
    # Get fields that need value discovery
    discovery_fields = []
    field_mappings = {}
    
    # From discovered filters - get actual field names, especially those marked for value discovery
    for filter_info in query_analysis.get("discovered_filters", []):
        field = filter_info.get("field")
        needs_discovery = filter_info.get("needs_value_discovery", False)
        if field and field in class_fields.get("field_names", []):
            if needs_discovery or field not in discovery_fields:
                discovery_fields.append(field)
    
    # From grouping - find actual field name
    if query_analysis.get("grouping"):
        grouping_term = query_analysis["grouping"]
        actual_field = find_semantically_similar_field(grouping_term, class_fields.get("field_names", []))
        if actual_field:
            discovery_fields.append(actual_field)
            field_mappings[grouping_term] = actual_field
    
    # From raw filters - map to actual fields and discover values
    for raw_filter in query_analysis.get("raw_filters", []):
        category = raw_filter.get("category")
        if category:
            # Map category to actual field
            mapped_filter = await map_filter_to_field(raw_filter, class_fields)
            if mapped_filter:
                field = mapped_filter["field"]
                if field not in discovery_fields:
                    discovery_fields.append(field)
                    field_mappings[category] = field
    
    # Now discover values for the identified fields
    enhanced_analysis["field_value_discovery"] = {}
    
    for field in discovery_fields:
        print(f"🔍 Discovering values for field: {field}")
        
        # Discover values for this field
        field_values = await discover_field_values(class_name, field, limit=50)
        
        enhanced_analysis["field_value_discovery"][field] = field_values
        
        # If values were discovered, enhance the filters
        if field_values["values"]:
            # Update discovered filters with better value mapping
            for filter_info in enhanced_analysis.get("discovered_filters", []):
                if filter_info.get("field") == field:
                    original_value = filter_info.get("value", "")
                    
                    # Try to find better matching value from discovered values
                    best_match = find_best_value_match(original_value, field_values["values"])
                    
                    if best_match and best_match != original_value:
                        filter_info["value"] = best_match
                        filter_info["value_source"] = "discovered"
                        filter_info["original_value"] = original_value
    
    # Update field mappings in analysis
    enhanced_analysis["field_mappings"] = field_mappings
    
    return enhanced_analysis

def find_best_value_match(search_value: str, available_values: list) -> str:
    """
    Find the best matching value from available values for a search term.
    Uses fuzzy matching to handle variations in user input.
    """
    if not available_values:
        return search_value
    
    search_lower = str(search_value).lower()
    
    # Exact match first
    for value in available_values:
        if str(value).lower() == search_lower:
            return value
    
    # Partial match
    for value in available_values:
        if search_lower in str(value).lower() or str(value).lower() in search_lower:
            return value
    
    # Fuzzy matching for common variations
    fuzzy_mappings = {
        "active": ["production", "enabled", "on", "running", "ongoing"],
        "inactive": ["obsolete", "disabled", "off", "stopped"],
        "new": ["pending", "draft", "created"],
        "closed": ["resolved", "completed", "done"],
        "open": ["active", "assigned", "in_progress", "ongoing", "new"]
    }
    
    for key, variations in fuzzy_mappings.items():
        if search_lower == key:
            for variation in variations:
                for value in available_values:
                    if variation in str(value).lower():
                        return value
    
    return search_value


# Comprehensive iTop Class Mapping for Smart Query Processing
ITOP_CLASS_TAXONOMY = {
    "SearchUseCases": [
      {
        "name": "Tickets",
        "classes": ["Ticket", "UserRequest", "Incident", "Problem", "Change"],
        "description": "ITSM ticket objects",
        "keywords": ["ticket", "tickets", "request", "requests", "issue", "issues", "incident", "incidents", "problem", "problems", "change", "changes", "support"]
      },
      {
        "name": "Change Requests",
        "classes": ["RoutineChange", "NormalChange", "ApprovedChange", "EmergencyChange"],
        "description": "Various types of change tickets",
        "keywords": ["change request", "change requests", "routine change", "normal change", "approved change", "emergency change"]
      },
      {
        "name": "PCs / End‑User Devices",
        "classes": ["PC", "PhysicalDevice"],
        "description": "Workstations and user-managed devices",
        "keywords": ["pc", "pcs", "computer", "computers", "desktop", "desktops", "laptop", "laptops", "workstation", "workstations"]
      },
      {
        "name": "Servers & Datacenter Devices",
        "classes": ["Server", "DatacenterDevice", "ConnectableCI"],
        "description": "Physical servers and datacenter assets",
        "keywords": ["server", "servers", "datacenter", "datacenter device", "connectable"]
      },
      {
        "name": "Virtual Machines",
        "classes": ["VirtualMachine", "Hypervisor"],
        "description": "Virtual infrastructure",
        "keywords": ["vm", "vms", "virtual machine", "virtual machines", "hypervisor", "hypervisors", "virtual"]
      },
      {
        "name": "Configuration Items",
        "classes": ["FunctionalCI"],
        "description": "Generic configuration item records",
        "keywords": ["ci", "configuration item", "functionalci"]
      },
      {
        "name": "Network Devices",
        "classes": ["NetworkDevice"],
        "description": "Routers, switches, firewalls, and the like",
        "keywords": ["network device", "router", "switch", "firewall", "network"]
      },
      {
        "name": "Racks, Locations & IPs",
        "classes": ["Rack", "Location", "PhysicalIP", "TapeLibrary"],
        "description": "Infrastructure placement and IP tracking",
        "keywords": ["rack", "location", "physical ip", "ip", "tape library"]
      }
    ],
    "PeopleAndOrganizations": [
      {
        "name": "People & Contacts",
        "classes": ["Person", "Contact"],
        "description": "Individual people and generic contacts",
        "keywords": ["person", "people", "contact", "contacts", "user", "users"]
      },
      {
        "name": "Teams & Organizations",
        "classes": ["Team", "Organization"],
        "description": "Groups or organizational entities",
        "keywords": ["team", "teams", "organization", "organizations", "org", "orgs"]
      }
    ],
    "ApplicationsAndServices": [
      {
        "name": "Applications & Software",
        "classes": ["ApplicationSolution", "SoftwareInstance", "Software", "SoftwarePatch", "Patch", "OSPatch"],
        "description": "Installed software, apps, and patches",
        "keywords": ["application", "applications", "software", "software instance", "patch", "os patch"]
      },
      {
        "name": "Services & SLAs",
        "classes": ["Service", "ServiceFamily", "ServiceSubcategory", "Contract", "ServiceSubcategory", "ServiceFamily", "SLA", "SLT", "CustomerContract", "ProviderContract"],
        "description": "Service entries and service agreements",
        "keywords": ["service", "services", "sla", "slas", "contract", "contracts"]
      }
    ],
    "LinkingClasses": [
      {
        "name": "Linking / Relationship Classes",
        "classes": [
          "lnkContactToTicket", "lnkDocumentToLicence", "lnkSoftwareInstanceToSoftwarePatch",
          "lnkFunctionalCIToTicket", "lnkVirtualDeviceToVolume", "lnkConnectableCIToNetworkDevice",
          "lnkPersonToTeam", "lnkSubnetToVLAN", "lnkGroupToCI", "lnkErrorToFunctionalCI",
          "lnkDocumentToError", "lnkContactToService", "lnkCustomerContractToService",
          "lnkCustomerContractToFunctionalCI", "lnkDocumentToTeam", "lnkNetworkDeviceToTeam",
          "lnkServerToTeam", "lnkFunctionalCIToProviderContract", "lnkFunctionalCIToService",
          "lnkFunctionalCIToTicket", "lnkDocumentToFunctionalCI", "lnkDocumentToSoftware",
          "lnkDocumentToPatch", "lnkContactToFunctionalCI", "lnkVirtualDeviceToVolume"
        ],
        "description": "Association/link tables between records",
        "keywords": ["link", "relationship", "lnk", "assoc", "association"]
      }
    ],
    "OperationalAndAudit": [
      {
        "name": "CMDB Change Logs",
        "classes": [
          "CMDBChange", "CMDBChangeOp", "CMDBChangeOpCreate", "CMDBChangeOpDelete",
          "CMDBChangeOpSetAttribute", "CMDBChangeOpSetAttributeCustomFields",
          "CMDBChangeOpSetAttributeLinks", "CMDBChangeOpSetAttributeLongText",
          "CMDBChangeOpSetAttributeHTML", "CMDBChangeOpSetAttributeURL",
          "CMDBChangeOpSetAttributeCaseLog", "CMDBChangeOpSetAttributeEncrypted",
          "CMDBChangeOpSetAttributeOneWayPassword", "CMDBChangeOpSetAttributeBlob",
          "CMDBChangeOpSetAttributeScalar"
        ],
        "description": "Detailed change tracking records",
        "keywords": ["cmdb", "change log", "audit"]
      },
      {
        "name": "Automation / Workflows / Notifications",
        "classes": ["Action", "ActionEmail", "ActionWebhook", "ActionSlackNotification", "Trigger", "TriggerOnObject", "TriggerOnObjectCreate", "TriggerOnStateChange", "TriggerOnPortalUpdate", "Event", "EventNotification", "EventWebhook"],
        "description": "Workflow actions, triggers, and events",
        "keywords": ["action", "trigger", "workflow", "event", "notification", "webhook"]
      },
      {
        "name": "Sync & Background Tasks",
        "classes": ["SynchroDataSource", "SynchroReplica", "SynchroAttribute", "SynchroAttExtKey", "SynchroAttLinkSet", "SynchroLog", "AsyncTask", "AsyncSendEmail", "BackgroundTask", "BulkExportResult"],
        "description": "External sync, jobs, and export results",
        "keywords": ["sync", "background", "task", "export", "async"]
      }
    ],
    "SecurityAndUI": [
      {
        "name": "Users & Profiles",
        "classes": ["User", "UserLocal", "UserExternal", "UserInternal", "UserLDAP", "UserToken", "PersonalToken", "URP_Profiles", "URP_UserOrg", "URP_UserProfile"],
        "description": "Authentication and user metadata",
        "keywords": ["user", "users", "profile", "profiles", "authentication", "token", "ldap", "urp"]
      },
      {
        "name": "UI Dashboard / Extensions",
        "classes": ["ModuleInstallation", "ExtensionInstallation", "UserDashboard", "Shortcut", "ShortcutOQL", "Query", "QueryOQL"],
        "description": "Modules, UI elements, and query definitions",
        "keywords": ["dashboard", "shortcut", "query", "module", "extension"]
      }
    ],
    "StorageAndDocuments": [
      {
        "name": "Documents & Attachments",
        "classes": ["Document", "DocumentFile", "DocumentNote", "DocumentWeb", "Attachment"],
        "description": "Stored documents and attachments",
        "keywords": ["document", "documents", "attachment", "attachments", "file", "files"]
      },
      {
        "name": "Storage Config",
        "classes": ["KeyValueStore", "DBProperty", "TemporaryObjectDescriptor"],
        "description": "System storage and config entries",
        "keywords": ["key", "store", "config", "dbproperty", "temporary"]
      }
    ],
    "InfrastructureMisc": [
      {
        "name": "Misc Infrastructure Tools",
        "classes": ["Typology", "Brand", "ContactType", "ContractType", "DocumentType", "IOSVersion", "Model", "OCSAssetCategory", "OCSSoftwareCategory", "OSFamily", "OSVersion", "RemoteApplicationType", "RemoteiTopConnectionToken", "RemoteApplicationConnection", "RemoteiTopConnection", "WebApplication", "DeliveryModel", "NAS", "StorageSystem", "SoftwareLicence", "Licence", "OSLicence", "CustomerContract", "ProviderContract", "ServiceFamily", "ServiceSubcategory", "Tape", "NASFileSystem", "LogicalVolume"],
        "description": "Various infra/categorization/config classes",
        "keywords": ["typology", "brand", "model", "license", "contract", "nas", "filesystem", "delivery", "webapp"]
      }
    ]
  }
# Cache for discovered class fields
_CLASS_FIELDS_CACHE = {}

async def discover_class_fields(class_name: str) -> dict:
    """
    Dynamically discover all available fields for a given iTop class.
    Returns ONLY the raw field names and sample values - NO HARDCODED CATEGORIZATION.
    Uses caching to avoid repeated API calls.
    """
    if class_name in _CLASS_FIELDS_CACHE:
        return _CLASS_FIELDS_CACHE[class_name]
    
    try:
        client = get_itop_client()
        
        # Get one object with all fields to discover the schema
        operation_data = {
            "operation": "core/get",
            "class": class_name,
            "key": f"SELECT {class_name}",
            "output_fields": "*",
            "limit": 1
        }
        
        result = await client.make_request(operation_data)
        
        if result.get("code") == 0 and result.get("objects"):
            # Extract field schema from the first object
            first_obj = next(iter(result["objects"].values()))
            if first_obj.get("code") == 0:
                fields = first_obj.get("fields", {})
                
                # Store ONLY raw field discovery - let AI decide what to display
                field_schema = {
                    "field_names": list(fields.keys()),
                    "sample_values": {k: str(v)[:100] if v else "" for k, v in fields.items()},
                    "total_fields": len(fields),
                    "key_fields": _identify_key_fields(fields),
                    "display_fields": _identify_display_fields(fields)
                }
                
                _CLASS_FIELDS_CACHE[class_name] = field_schema
                return field_schema
    
    except Exception as e:
        # Return empty schema if discovery fails
        return {
            "field_names": [],
            "sample_values": {},
            "total_fields": 0,
            "key_fields": [],
            "display_fields": []
        }
    
    return _CLASS_FIELDS_CACHE.get(class_name, {})


def _identify_key_fields(fields: dict) -> list:
    """Identify the most important fields for summary display"""
    priority_indicators = [
        "name", "friendlyname", "title", "status", "id", "ref", 
        "description", "organization_name", "org_name", "caller_name"
    ]
    
    key_fields = []
    for indicator in priority_indicators:
        if indicator in fields and fields[indicator]:
            key_fields.append(indicator)
    
    return key_fields[:5]  # Top 5 key fields


def _identify_display_fields(fields: dict) -> list:
    """Identify the best fields for table/summary display"""
    # Skip very long text fields, internal IDs, and empty fields
    skip_patterns = ["_id", "_list", "html", "description", "solution", "log"]
    
    display_fields = []
    for field_name, field_value in fields.items():
        if (field_value and 
            not any(pattern in field_name.lower() for pattern in skip_patterns) and
            len(str(field_value)) < 200):  # Skip very long values
            display_fields.append(field_name)
    
    return display_fields[:8]  # Top 8 display fields

def smart_class_detection(query: str) -> tuple[str, float, dict]:
    """
    Returns:
        tuple: (best_class_name, confidence_score, query_analysis)
    """
    query_lower = query.lower()
    best_matches = []
    
    # SPECIAL CASE 1: Change requests should use Change class (CHECK FIRST!)
    change_patterns = ["change request", "change requests"]
    for pattern in change_patterns:
        if pattern in query_lower:
            return "Change", 0.95, {"action": "list", "time_analysis": True}
    
    # SPECIAL CASE 2: SLA/support ticket queries should use UserRequest  
    sla_patterns = ["sla", "support ticket", "support tickets", "sla issues", "with sla"]
    for pattern in sla_patterns:
        if pattern in query_lower and "change" not in query_lower:
            # Force UserRequest for SLA queries (but not for change requests)
            return "UserRequest", 0.95, {"action": "list", "time_analysis": True}
    
    # Search through all categories and classes
    for category_list in ITOP_CLASS_TAXONOMY.values():
        for category in category_list:
            for class_name in category["classes"]:
                score = 0
                
                # Direct class name match (high score)
                if class_name.lower() in query_lower:
                    score += 50
                
                # Keyword matching
                for keyword in category.get("keywords", []):
                    if keyword in query_lower:
                        score += len(keyword.split()) * 10  # Multi-word keywords get higher scores
                
                # Pattern matching for specific query types
                if score > 0:
                    best_matches.append((class_name, score, category))
    
    # Sort by score and return the best match
    best_matches.sort(key=lambda x: x[1], reverse=True)
    
    if best_matches:
        best_class, best_score, best_category = best_matches[0]
        
        # Analyze query for additional parameters
        query_analysis = analyze_query_intent(query, best_class)
        
        # Normalize confidence score (0-1)
        confidence = min(best_score / 100.0, 1.0)
        
        return best_class, confidence, query_analysis
    
    # Default fallback
    return "UserRequest", 0.1, {"action": "list", "filters": []}

def analyze_query_intent_with_schema(query: str, class_name: str, class_fields: dict) -> dict:
    """
    Analyze the query to extract intent, filters, and desired actions using actual schema knowledge.
    This is the NEW improved version that uses discovered fields for better mapping.
    """
    query_lower = query.lower()
    available_fields = class_fields.get("field_names", [])
    
    analysis = {
        "action": "list",  # Default action
        "raw_filters": [],  # Raw filter terms to be mapped dynamically
        "requested_fields": [],  # Fields specifically requested in the query
        "grouping": None,
        "sorting": None,
        "format_preference": "detailed",
        "time_analysis": False,
        "comparison": False,
        "discovered_filters": []  # NEW: Pre-mapped filters using schema
    }
    
    # Detect action type (same as before)
    if any(word in query_lower for word in ["count", "how many", "number of"]):
        analysis["action"] = "count"
        analysis["format_preference"] = "summary"
    elif any(word in query_lower for word in ["compare", "vs", "versus", "compared to"]):
        analysis["action"] = "compare"
        analysis["comparison"] = True
        analysis["format_preference"] = "table"
        
        # Detect multi-query patterns like "closed vs open", "active vs inactive"
        if " vs " in query_lower or " versus " in query_lower:
            vs_parts = query_lower.replace(" versus ", " vs ").split(" vs ")
            if len(vs_parts) == 2:
                analysis["comparison_values"] = [vs_parts[0].strip().split()[-1], vs_parts[1].strip().split()[0]]
                analysis["needs_multi_query"] = True
    elif any(word in query_lower for word in ["stats", "statistics", "breakdown", "summary", "based stats", "by status", "group by"]):
        analysis["action"] = "statistics"
        analysis["format_preference"] = "table"
    elif any(word in query_lower for word in ["list", "show", "get", "find"]):
        analysis["action"] = "list"
    
    # NEW: Smart field-aware filtering using discovered schema
    discovered_filters = extract_filters_with_schema(query_lower, available_fields)
    analysis["discovered_filters"] = discovered_filters
    
    # Also keep the old system for backward compatibility
    raw_filters = extract_filter_terms_from_query(query_lower)
    analysis["raw_filters"] = raw_filters
    
    # Detect grouping with schema awareness
    if "by" in query_lower:
        parts = query_lower.split("by")
        if len(parts) > 1:
            group_part = parts[-1].strip()
            group_words = group_part.split()
            if group_words:
                # Try to find actual field that matches grouping intent
                potential_group_field = find_semantically_similar_field(group_words[0], class_fields.get("field_names", []))
                analysis["grouping"] = potential_group_field or group_words[0]
    elif "based" in query_lower and "stats" in query_lower:
        # Handle "status based stats" type queries
        if "status" in query_lower:
            status_fields = [f for f in available_fields if "status" in f.lower()]
            if status_fields:
                analysis["grouping"] = status_fields[0]  # Use first status field found
    
    # Detect time-based analysis with schema awareness
    if any(word in query_lower for word in ["on time", "late", "overdue", "sla", "deadline"]):
        analysis["time_analysis"] = True
        # Look for actual SLA-related fields in the schema
        sla_fields = [f for f in available_fields if any(sla_term in f.lower() for sla_term in ["sla", "deadline", "due", "timeout"])]
        if sla_fields:
            analysis["sla_fields"] = sla_fields
    
    return analysis

def extract_filters_with_schema(query_lower: str, available_fields: list) -> list:
    """
    NEW: Extract filters using actual schema knowledge for much better accuracy.
    Now also detects comparison patterns like "closed vs open".
    """
    filters = []
    
    # Detect comparison patterns first (e.g., "closed vs open", "ongoing vs resolved")
    comparison_patterns = [
        r'\b(\w+)\s+vs\s+(\w+)\b',
        r'\b(\w+)\s+versus\s+(\w+)\b',
        r'\b(\w+)\s+compared?\s+to\s+(\w+)\b'
    ]
    
    comparison_values = []
    for pattern in comparison_patterns:
        matches = re.findall(pattern, query_lower)
        for match in matches:
            comparison_values.extend(match)
    
    if comparison_values:
        print(f"🔍 Detected comparison values: {comparison_values}")
        
        # Find the best field for these comparison values
        status_fields = [f for f in available_fields if "status" in f.lower() or "state" in f.lower()]
        best_field = status_fields[0] if status_fields else "status"
        
        # Create filters for each comparison value
        for value in comparison_values:
            filters.append({
                "field": best_field,
                "operator": "=",
                "value": value,
                "confidence": "medium",
                "source": "comparison_detection",
                "is_comparison_value": True,  # Mark as comparison value for multi-query
                "needs_value_discovery": True,
                "assume_value": False
            })
    
    # Status filtering - find actual status fields
    status_fields = [f for f in available_fields if "status" in f.lower() or "state" in f.lower()]
    status_terms = ["new", "assigned", "pending", "resolved", "closed", "open", "ongoing", "active", "inactive", "production", "obsolete"]
    
    # Skip status terms if they're already handled by comparison detection
    handled_terms = set(comparison_values)
    
    for term in status_terms:
        if term in query_lower and term not in handled_terms and status_fields:
            # DON'T assume the value exists - just mark the field for discovery
            filters.append({
                "field": status_fields[0],  # Use the first/best status field
                "operator": "=",
                "value": term,
                "confidence": "low",  # Very low confidence since we haven't verified the value exists
                "source": "schema_aware",
                "needs_value_discovery": True,  # MUST discover actual values first
                "assume_value": False  # Don't use this filter until values are discovered
            })
    
    # OS filtering - find actual OS fields
    os_fields = [f for f in available_fields if any(os_term in f.lower() for os_term in ["os", "operating", "system", "platform", "osfamily", "osversion"])]
    os_terms = ["linux", "windows", "ubuntu", "centos", "redhat", "debian", "fedora", "macos"]
    
    for term in os_terms:
        if term in query_lower and os_fields:
            # Prefer family fields for OS family terms
            family_fields = [f for f in os_fields if "family" in f.lower()]
            best_field = family_fields[0] if family_fields else os_fields[0]
            filters.append({
                "field": best_field,
                "operator": "LIKE",
                "value": f"%{term}%",
                "confidence": "high",
                "source": "schema_aware"
            })
    
    # Memory/RAM filtering - find actual memory fields
    memory_fields = [f for f in available_fields if any(mem_term in f.lower() for mem_term in ["ram", "memory", "mem"])]
    ram_pattern = r'(\d+)\s*(gb|mb)\s*(ram|memory)'
    ram_match = re.search(ram_pattern, query_lower)
    if ram_match and memory_fields:
        amount = int(ram_match.group(1))
        unit = ram_match.group(2)
        amount_mb = amount * 1024 if unit == "gb" else amount
        
        operator = ">"
        if "less than" in query_lower or "under" in query_lower or "below" in query_lower:
            operator = "<"
        elif "at least" in query_lower:
            operator = ">="
        elif "at most" in query_lower:
            operator = "<="
            
        filters.append({
            "field": memory_fields[0],
            "operator": operator,
            "value": amount_mb,
            "confidence": "high",
            "source": "schema_aware"
        })
    
    # Organization/Team/Service filtering - find relationship fields
    relationship_terms = {
        "organization": ["org", "company", "organization"],
        "team": ["team", "group"],
        "service": ["service", "application", "app"],
        "caller": ["caller", "user", "person"],
        "agent": ["agent", "assignee", "owner"]
    }
    
    for rel_type, rel_keywords in relationship_terms.items():
        rel_fields = [f for f in available_fields if any(keyword in f.lower() for keyword in rel_keywords)]
        if rel_fields:
            # Look for mentions of specific names after these keywords
            for keyword in rel_keywords:
                if keyword in query_lower:
                    # Extract potential names after the keyword
                    parts = query_lower.split(keyword)
                    if len(parts) > 1:
                        after_keyword = parts[1].strip()
                        words = after_keyword.split()
                        if words and len(words[0]) > 2:  # Reasonable name length
                            name_field = None
                            id_field = None
                            for field in rel_fields:
                                if field.endswith("_name"):
                                    name_field = field
                                elif field.endswith("_id"):
                                    id_field = field
                            
                            best_field = name_field or id_field or rel_fields[0]
                            filters.append({
                                "field": best_field,
                                "operator": "LIKE",
                                "value": f"%{words[0]}%",
                                "confidence": "medium",
                                "source": "schema_aware"
                            })
    
    return filters

def analyze_query_intent(query: str, class_name: str) -> dict:
    """
    Analyze the query to extract intent, filters, and desired actions.
    This function now extracts raw filter terms without hardcoded field mappings.
    """
    query_lower = query.lower()
    analysis = {
        "action": "list",  # Default action
        "raw_filters": [],  # Raw filter terms to be mapped dynamically
        "requested_fields": [],  # Fields specifically requested in the query
        "grouping": None,
        "sorting": None,
        "format_preference": "detailed",
        "time_analysis": False,
        "comparison": False
    }
    
    # Detect action type
    if any(word in query_lower for word in ["count", "how many", "number of"]):
        analysis["action"] = "count"
        analysis["format_preference"] = "summary"
    elif any(word in query_lower for word in ["compare", "vs", "versus", "compared to"]):
        analysis["action"] = "compare"
        analysis["comparison"] = True
        analysis["format_preference"] = "table"
    elif any(word in query_lower for word in ["stats", "statistics", "breakdown", "summary"]):
        analysis["action"] = "statistics"
        analysis["format_preference"] = "table"
    elif any(word in query_lower for word in ["list", "show", "get", "find"]):
        analysis["action"] = "list"
    
    # Extract raw filter terms from the query
    raw_filters = extract_filter_terms_from_query(query_lower)
    analysis["raw_filters"] = raw_filters
    
    # Detect grouping
    if "by" in query_lower:
        # Extract what to group by
        parts = query_lower.split("by")
        if len(parts) > 1:
            group_part = parts[-1].strip()
            # Extract the first meaningful word after "by"
            group_words = group_part.split()
            if group_words:
                analysis["grouping"] = group_words[0]
    
    # Detect time-based analysis
    if any(word in query_lower for word in ["on time", "late", "overdue", "sla", "deadline"]):
        analysis["time_analysis"] = True
    
    return analysis

def extract_filter_terms_from_query(query_lower: str) -> list:
    """
    Extract filter terms from natural language query.
    Returns a list of dictionaries with filter information.
    """
    filters = []
    
    # Status-related terms
    status_terms = {
        "new": {"term": "new", "category": "status"},
        "assigned": {"term": "assigned", "category": "status"},
        "pending": {"term": "pending", "category": "status"},
        "resolved": {"term": "resolved", "category": "status"},
        "closed": {"term": "closed", "category": "status"},
        "open": {"term": "open", "category": "status"},
        "ongoing": {"term": "ongoing", "category": "status"},
        "active": {"term": "active", "category": "status"},
        "inactive": {"term": "inactive", "category": "status"},
        "production": {"term": "production", "category": "status"},
        "obsolete": {"term": "obsolete", "category": "status"}
    }
    
    # OS-related terms
    os_terms = {
        "linux": {"term": "linux", "category": "os"},
        "windows": {"term": "windows", "category": "os"},
        "ubuntu": {"term": "ubuntu", "category": "os"},
        "centos": {"term": "centos", "category": "os"},
        "redhat": {"term": "redhat", "category": "os"}
    }
    
    # Priority/urgency terms
    priority_terms = {
        "high": {"term": "high", "category": "priority"},
        "medium": {"term": "medium", "category": "priority"},
        "low": {"term": "low", "category": "priority"},
        "urgent": {"term": "urgent", "category": "priority"},
        "critical": {"term": "critical", "category": "priority"}
    }
    
    # Null/empty checks
    null_terms = ["null", "empty", "without", "missing", "no ", "blank"]
    
    # Check for status terms
    for term, info in status_terms.items():
        if term in query_lower:
            filters.append({
                "search_term": term,
                "category": info["category"],
                "operator": "=",
                "value": info["term"]
            })
    
    # Check for OS terms
    for term, info in os_terms.items():
        if term in query_lower:
            filters.append({
                "search_term": term,
                "category": info["category"],
                "operator": "LIKE",
                "value": f"%{info['term']}%"
            })
    
    # Check for priority terms
    for term, info in priority_terms.items():
        if term in query_lower:
            filters.append({
                "search_term": term,
                "category": info["category"],
                "operator": "=",
                "value": info["term"]
            })
    
    # Check for RAM/Memory constraints
    import re
    ram_pattern = r'(\d+)\s*(gb|mb)\s*(ram|memory)'
    ram_match = re.search(ram_pattern, query_lower)
    if ram_match:
        amount = int(ram_match.group(1))
        unit = ram_match.group(2)
        # Convert to MB for consistency
        if unit == "gb":
            amount_mb = amount * 1024
        else:
            amount_mb = amount
            
        # Determine operator based on context
        operator = "<"
        if "more than" in query_lower or "greater than" in query_lower or "above" in query_lower:
            operator = ">"
        elif "less than" in query_lower or "under" in query_lower or "below" in query_lower:
            operator = "<"
        elif "at least" in query_lower:
            operator = ">="
        elif "at most" in query_lower:
            operator = "<="
            
        filters.append({
            "search_term": f"{ram_match.group(1)} {unit}",
            "category": "memory",
            "operator": operator,
            "value": amount_mb
        })
    
    # Check for null/empty field queries
    for null_term in null_terms:
        if null_term in query_lower:
            # Try to identify what field should be null
            context_words = query_lower.split()
            null_index = -1
            for i, word in enumerate(context_words):
                if null_term in word:
                    null_index = i
                    break
            
            if null_index >= 0:
                # Look for field indicators nearby
                search_range = context_words[max(0, null_index-2):min(len(context_words), null_index+3)]
                field_indicators = ["service", "category", "organization", "team", "agent", "caller"]
                
                for indicator in field_indicators:
                    if indicator in " ".join(search_range):
                        filters.append({
                            "search_term": f"{null_term} {indicator}",
                            "category": indicator,
                            "operator": "IS NULL",
                            "value": None
                        })
                        break
    
    return filters



async def map_filter_to_field(filter_info: dict, class_fields: dict) -> dict:
    """
    Use dynamic field mapping to find the best field match for a filter term.
    Uses only dynamically discovered fields without hardcoded categorization.
    """
    search_term = filter_info["search_term"]
    category = filter_info["category"]
    operator = filter_info["operator"]
    value = filter_info["value"]
    
    available_fields = class_fields.get("field_names", [])
    if not available_fields:
        return None
    
    # Dynamic field mapping logic - no hardcoded categories
    best_field = None
    
    if category == "status":
        # Look for fields containing "status" or "state"
        for field in available_fields:
            field_lower = field.lower()
            if "status" in field_lower or "state" in field_lower:
                best_field = field
                break
    
    elif category == "os":
        # Look for OS-related fields
        os_candidates = []
        for field in available_fields:
            field_lower = field.lower()
            if any(term in field_lower for term in ["os", "operating", "system", "platform", "osfamily", "osversion"]):
                os_candidates.append(field)
        
        # Prefer osfamily_name for OS family terms, then other OS fields
        if os_candidates:
            family_fields = [f for f in os_candidates if "family" in f.lower()]
            if family_fields:
                best_field = family_fields[0]
            else:
                best_field = min(os_candidates, key=len)
    
    elif category == "memory":
        # Look for memory/RAM-related fields
        memory_candidates = []
        for field in available_fields:
            field_lower = field.lower()
            if any(term in field_lower for term in ["ram", "memory", "mem"]):
                memory_candidates.append(field)
        
        if memory_candidates:
            best_field = min(memory_candidates, key=len)
    
    elif category == "priority":
        # Look for priority/urgency fields
        priority_candidates = []
        for field in available_fields:
            field_lower = field.lower()
            if any(term in field_lower for term in ["priority", "urgency"]):
                priority_candidates.append(field)
        
        if priority_candidates:
            best_field = min(priority_candidates, key=len)
    
    elif category in ["service", "organization", "team", "agent", "caller", "category"]:
        # Look for relationship fields
        relationship_candidates = []
        for field in available_fields:
            field_lower = field.lower()
            # Look for exact match first
            if category in field_lower:
                relationship_candidates.append(field)
            # Also look for ID versions
            elif f"{category}_id" in field_lower:
                relationship_candidates.append(field)
        
        if relationship_candidates:
            # Prefer ID fields for relationships when doing NULL checks
            if operator == "IS NULL":
                id_fields = [f for f in relationship_candidates if "_id" in f.lower()]
                if id_fields:
                    best_field = id_fields[0]
                else:
                    best_field = relationship_candidates[0]
            else:
                best_field = relationship_candidates[0]
    
    # If no specific mapping found, try semantic similarity
    if not best_field:
        best_field = find_semantically_similar_field(search_term, available_fields)
    
    if best_field:
        return {
            "field": best_field,
            "operator": operator,
            "value": value,
            "original_term": search_term
        }
    
    return None

def find_semantically_similar_field(search_term: str, available_fields: list) -> str:
    """
    Find the most semantically similar field name for a search term.
    Uses simple string similarity and common patterns.
    """
    if not available_fields:
        return None
    
    search_lower = search_term.lower()
    best_field = None
    best_score = 0
    
    for field in available_fields:
        field_lower = field.lower()
        score = 0
        
        # Exact substring match gets high score
        if search_lower in field_lower:
            score += 50
        
        # Partial word matches
        search_words = search_lower.split()
        field_words = field_lower.replace("_", " ").split()
        
        for search_word in search_words:
            for field_word in field_words:
                if search_word == field_word:
                    score += 20
                elif search_word in field_word or field_word in search_lower:
                    score += 10
        
        # Bonus for common field patterns
        if field_lower.endswith("_name") or field_lower.endswith("_id"):
            score += 5
        
        if score > best_score:
            best_score = score
            best_field = field
    
    return best_field if best_score > 0 else None

async def build_smart_oql_query(class_name: str, query_analysis: dict, class_fields: dict) -> tuple[str, dict]:
    """
    Build an OQL query based on the analysis and available fields.
    NOW uses schema-aware filters for much better accuracy.
    
    Returns:
        tuple: (oql_query, validation_info)
        - oql_query: The built OQL query string
        - validation_info: Dict with validation status and multi-query needs
    """
    base_query = f"SELECT {class_name}"
    conditions = []
    validation_info = {
        "has_unvalidated_filters": False,
        "needs_multi_query": False,
        "comparison_values": [],
        "skipped_filters": []
    }
    
    # Detect comparison queries that need multi-query execution
    comparison_values = []
    for filter_info in query_analysis.get("discovered_filters", []):
        if filter_info.get("is_comparison_value", False):
            comparison_values.append(filter_info["value"])
    
    if len(comparison_values) > 1:
        validation_info["needs_multi_query"] = True
        validation_info["comparison_values"] = comparison_values
        print(f"🔄 Detected multi-query need for comparison: {comparison_values}")
        # For multi-query, return base query without comparison filters
        # The caller will handle running separate queries for each value
        non_comparison_filters = [f for f in query_analysis.get("discovered_filters", []) 
                                 if not f.get("is_comparison_value", False)]
        query_analysis["discovered_filters"] = non_comparison_filters
    
    # Process NEW schema-aware filters first (higher priority) - BUT ONLY VALIDATED ONES
    for filter_info in query_analysis.get("discovered_filters", []):
        field = filter_info["field"]
        operator = filter_info["operator"]
        value = filter_info["value"]
        assume_value = filter_info.get("assume_value", True)  # Default to True for backward compatibility
        
        # CRITICAL: Only apply filters if values have been validated OR explicitly allowed
        if not assume_value:
            print(f"⚠️ Skipping unvalidated filter: {field} = '{value}' (needs value discovery)")
            validation_info["has_unvalidated_filters"] = True
            validation_info["skipped_filters"].append({
                "field": field,
                "operator": operator,
                "value": value,
                "reason": "unvalidated"
            })
            continue
        
        if operator == "IS NULL":
            if field.endswith("_id") or field.lower() in ["service_id", "organization_id", "team_id"]:
                conditions.append(f"({field} = '' OR {field} = 0)")
            else:
                conditions.append(f"{field} = ''")
        elif operator == "LIKE":
            conditions.append(f"{field} LIKE '{value}'")
        elif operator in ["<", ">", "<=", ">="]:
            conditions.append(f"{field} {operator} {value}")
        else:
            conditions.append(f"{field} = '{value}'")
    
    # Fallback to old system for unmapped filters
    mapped_filters = []
    for raw_filter in query_analysis.get("raw_filters", []):
        mapped_filter = await map_filter_to_field(raw_filter, class_fields)
        if mapped_filter:
            mapped_filters.append(mapped_filter)
    
    # Build conditions from fallback mapped filters (only if not already covered)
    existing_fields = {f["field"] for f in query_analysis.get("discovered_filters", [])}
    for mapped_filter in mapped_filters:
        field = mapped_filter["field"]
        if field in existing_fields:
            continue  # Skip if already handled by schema-aware filters
            
        operator = mapped_filter["operator"]
        value = mapped_filter["value"]
        
        if operator == "IS NULL":
            if field.endswith("_id") or field.lower() in ["service_id", "organization_id", "team_id"]:
                conditions.append(f"({field} = '' OR {field} = 0)")
            else:
                conditions.append(f"{field} = ''")
        elif operator == "LIKE":
            conditions.append(f"{field} LIKE '{value}'")
        elif operator in ["<", ">", "<=", ">="]:
            conditions.append(f"{field} {operator} {value}")
        else:
            conditions.append(f"{field} = '{value}'")
    
    # Handle special time analysis with schema awareness - IMPROVED
    if query_analysis.get("time_analysis"):
        sla_fields = query_analysis.get("sla_fields", [])
        if sla_fields:
            sla_focus = query_analysis.get("sla_focus", "all")
            
            # Better SLA field selection and condition building
            if sla_focus == "violations":
                # Look for SLA violation indicators
                sla_violation_fields = [f for f in sla_fields if any(term in f.lower() for term in 
                                                                  ["passed", "violated", "breach", "missed"])]
                
                if sla_violation_fields:
                    # First preference: status field like sla_passed, sla_violated, etc.
                    conditions.append(f"{sla_violation_fields[0]} = 'yes'")
                elif any("deadline" in f.lower() for f in sla_fields):
                    # Second preference: deadline field for date comparison
                    deadline_field = next(f for f in sla_fields if "deadline" in f.lower())
                    conditions.append(f"{deadline_field} < NOW()")
                elif any("sla" in f.lower() and "status" in f.lower() for f in sla_fields):
                    # Third preference: status field
                    status_field = next(f for f in sla_fields if "sla" in f.lower() and "status" in f.lower())
                    conditions.append(f"{status_field} = 'breached'")
            
            elif sla_focus == "compliant":
                # Look for SLA compliance indicators
                sla_violation_fields = [f for f in sla_fields if any(term in f.lower() for term in 
                                                                  ["passed", "violated", "breach", "missed"])]
                
                if sla_violation_fields:
                    # First preference: status field showing NOT violated
                    conditions.append(f"{sla_violation_fields[0]} = 'no'")
                elif any("deadline" in f.lower() for f in sla_fields):
                    # Second preference: deadline in future
                    deadline_field = next(f for f in sla_fields if "deadline" in f.lower())
                    conditions.append(f"{deadline_field} > NOW()")
                elif any("sla" in f.lower() and "status" in f.lower() for f in sla_fields):
                    # Third preference: status field
                    status_field = next(f for f in sla_fields if "sla" in f.lower() and "status" in f.lower())
                    conditions.append(f"{status_field} = 'within'")
            else:
                # Default when no specific focus - just look for any SLA fields without conditions
                # This will return all records with SLA data
                pass
    
    # Build final query
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    
    return base_query, validation_info

def determine_smart_output_fields(query_analysis: dict, class_fields: dict, output_format: str) -> str:
    """
    SMART OUTPUT FIELD SELECTION
    
    Determines the optimal output fields based on:
    - Query intent and action type
    - Discovered schema and available fields
    - Requested output format
    - SLA/status/grouping requirements
    """
    available_fields = class_fields.get("field_names", [])
    key_fields = class_fields.get("key_fields", ["id", "name"])
    display_fields = class_fields.get("display_fields", [])
    
    # For count queries - if grouping is needed, include the grouping field
    if query_analysis.get("action") == "count":
        if query_analysis.get("grouping"):
            grouping_field = query_analysis["grouping"]
            # Map grouping field to actual field name if needed
            actual_grouping_field = find_semantically_similar_field(grouping_field, available_fields)
            if actual_grouping_field:
                return f"id,{actual_grouping_field}"
            else:
                return f"id,{grouping_field}"
        else:
            return "id"  # Simple count, minimal fields needed
    
    # For statistics/breakdown queries - need relevant fields for analysis
    if query_analysis.get("action") in ["statistics", "compare"]:
        needed_fields = set(["id"])
        
        # Add status-related fields
        status_fields = [f for f in available_fields if any(term in f.lower() for term in ["status", "state"])]
        needed_fields.update(status_fields[:2])  # Top 2 status fields
        
        # Add grouping field if specified
        if query_analysis.get("grouping"):
            grouping_field = find_semantically_similar_field(query_analysis["grouping"], available_fields)
            if grouping_field:
                needed_fields.add(grouping_field)
        
        # Add SLA/time fields for SLA-related queries
        if query_analysis.get("time_analysis"):
            sla_fields = [f for f in available_fields if any(term in f.lower() for term in ["sla", "deadline", "due", "timeout", "resolution"])]
            needed_fields.update(sla_fields[:3])  # Top 3 SLA fields
        
        # Add key display fields
        needed_fields.update(key_fields[:3])
        
        return ",".join(sorted(needed_fields))
    
    # For summary format - use key fields plus any fields mentioned in filters
    if output_format == "summary":
        needed_fields = set(key_fields)
        
        # Add fields from discovered filters
        for filter_info in query_analysis.get("discovered_filters", []):
            field = filter_info.get("field")
            if field and field in available_fields:
                needed_fields.add(field)
        
        return ",".join(sorted(needed_fields)) if needed_fields else "*"
    
    # For table format - use display fields plus filter fields
    if output_format == "table":
        needed_fields = set(display_fields[:8])  # Top 8 display fields
        
        # Add fields from discovered filters
        for filter_info in query_analysis.get("discovered_filters", []):
            field = filter_info.get("field")
            if field and field in available_fields:
                needed_fields.add(field)
        
        return ",".join(sorted(needed_fields)) if needed_fields else "*"
    
    # For detailed view - get ALL fields for maximum information
    return "*"


async def handle_multi_class_query(query: str, query_analysis: dict) -> str:
    """
    Handle queries that need data from multiple classes like "network devices with their locations"
    """
    query_lower = query.lower()
    
    # Pattern: "X with their Y" or "X and their Y"
    if any(pattern in query_lower for pattern in ["with their", "and their", "with location", "and location"]):
        
        # Network devices with locations
        if any(term in query_lower for term in ["network device", "network devices"]):
            if any(term in query_lower for term in ["location", "locations"]):
                return await query_network_devices_with_locations()
        
        # TODO: Add more multi-class patterns later
        # - Servers with applications
        # - Users with tickets
    
    return None  # Not a multi-class query

async def query_network_devices_with_locations() -> str:
    """Query network devices and their locations using proper field relationships"""
    try:
        client = get_itop_client()
        
        # First get all network devices
        devices_op = {
            "operation": "core/get",
            "class": "NetworkDevice",
            "key": "SELECT NetworkDevice",
            "output_fields": "*",
            "limit": 100
        }
        
        devices_result = await client.make_request(devices_op)
        
        if devices_result.get("code") != 0:
            return f"❌ Error getting network devices: {devices_result.get('message')}"
        
        devices = devices_result.get("objects", {})
        if not devices:
            return "No network devices found."
        
        # Get all locations for reference
        locations_op = {
            "operation": "core/get", 
            "class": "Location",
            "key": "SELECT Location",
            "output_fields": "*",
            "limit": 100
        }
        
        locations_result = await client.make_request(locations_op)
        locations = {}
        
        if locations_result.get("code") == 0:
            for loc_key, loc_data in locations_result.get("objects", {}).items():
                if loc_data.get("code") == 0:
                    loc_fields = loc_data.get("fields", {})
                    loc_id = loc_fields.get("id")
                    if loc_id:
                        locations[str(loc_id)] = loc_fields.get("name", "Unknown Location")
        
        # Format output combining device + location info
        output = f"**Network Devices with Locations**\n\n"
        output += f"Found {len(devices)} network device(s):\n\n"
        
        for device_key, device_data in devices.items():
            if device_data.get("code") == 0:
                device_fields = device_data.get("fields", {})
                device_name = device_fields.get("name", "Unknown Device")
                
                # Try to find location using common location field patterns
                location_name = "No Location"
                for field_name, field_value in device_fields.items():
                    if field_value and any(loc_term in field_name.lower() for loc_term in ["location", "site", "building"]):
                        if str(field_value) in locations:
                            location_name = locations[str(field_value)]
                        else:
                            location_name = str(field_value)
                        break
                
                output += f"🔹 **{device_name}** → Location: {location_name}\n"
                
                # Show other relevant device info
                relevant_fields = ["ip_address", "status", "brand_name", "model_name", "organization_name"]
                for field in relevant_fields:
                    if field in device_fields and device_fields[field]:
                        output += f"   {field}: {device_fields[field]}\n"
                output += "\n"
        
        return output
        
    except Exception as e:
        return f"❌ Error in multi-class query: {str(e)}"

@mcp.tool()
async def smart_query_processor(
    query: str,
    force_class: Optional[str] = None,
    output_format: str = "auto",
    limit: int = 100
) -> str:
    """
    **SMART iTop QUERY PROCESSOR**
    
    Steps:
    1. Detect best iTop class from query (or use force_class)
    2. Discover class schema (fields)
    3. Analyze query intent using schema
    4. Map filters to real fields
    5. Build OQL query with schema-based conditions
    6. Execute query with optimal fields
    7. Format output (detailed, summary, table, json)
    
    Features:

    - Schema-aware: maps natural language to real fields
    - Handles filters, grouping, SLA, dates, relationships
    - No arbitrary limits; user controls output
    
    Params:
    - query: Natural language
    - force_class: Optional class override
    - output_format: auto, detailed, summary, table, json
    - limit: Max results
    """
    try:
        if limit < 1:
            limit = 1
        
        # Step 0: Check if this is a multi-class query first
        multi_class_result = await handle_multi_class_query(query, {})
        if multi_class_result:
            return multi_class_result
            
        # Step 1: Detect the best class or use forced class (initial detection)
        if force_class:
            class_name = force_class
            confidence = 1.0
        else:
            class_name, confidence, _ = smart_class_detection(query)
            
            # Step 1.5: For SLA queries, verify the class has SLA fields
            if any(term in query.lower() for term in ["sla", "on time", "overdue", "deadline"]) and class_name != "UserRequest":
                # Check if detected class has SLA fields, if not, try UserRequest
                temp_client = get_itop_client()
                temp_schema = {
                    "operation": "core/get",
                    "class": class_name,
                    "key": f"SELECT {class_name}",
                    "output_fields": "*",
                    "limit": 1
                }
                temp_result = await temp_client.make_request(temp_schema)
                
                if temp_result.get("code") == 0 and temp_result.get("objects"):
                    first_obj = next(iter(temp_result["objects"].values()))
                    if first_obj.get("code") == 0:
                        fields = first_obj.get("fields", {})
                        sla_fields = [f for f in fields.keys() if any(sla_term in f.lower() for sla_term in ["sla", "deadline", "due", "timeout"])]
                        
                        # If no SLA fields found, switch to UserRequest
                        if not sla_fields:
                            print(f"🔄 No SLA fields found in {class_name}, switching to UserRequest for SLA query")
                            class_name = "UserRequest"
                            confidence = 0.9
        
        client = get_itop_client()
        schema_operation = {
            "operation": "core/get",
            "class": class_name,
            "key": f"SELECT {class_name}",
            "output_fields": "*",
            "limit": 1
        }
        
        schema_result = await client.make_request(schema_operation)
        
        if schema_result.get("code") != 0:
            return f"❌ **Schema Discovery Error**: {schema_result.get('message', 'Unknown error')}"
        
        schema_objects = schema_result.get("objects", {})
        class_fields = {}
        
        if schema_objects:
            first_obj = next(iter(schema_objects.values()))
            if first_obj.get("code") == 0:
                all_fields = first_obj.get("fields", {})
                class_fields = {
                    "field_names": list(all_fields.keys()),
                    "sample_values": {k: str(v)[:100] if v else "" for k, v in all_fields.items()},  # No truncation
                    "total_fields": len(all_fields),
                    "key_fields": _identify_key_fields(all_fields),
                    "display_fields": _identify_display_fields(all_fields)
                }
        
        # Step 3: NOW do intent analysis with schema knowledge
        query_analysis = analyze_query_intent_with_schema(query, class_name, class_fields)
        
        # Step 3.5: INTELLIGENCE LAYER - Classify query complexity and decide on value discovery
        query_complexity = classify_query_complexity(query, query_analysis)
        
       
        
        # Step 3.6: SMART VALUE DISCOVERY - Only when needed for complex queries
        if query_complexity['needs_value_discovery']:
            print(f"🔍 Performing intelligent value discovery for {len(query_complexity['discovery_fields'])} fields...")
            query_analysis = await enhance_query_analysis_with_values(query_analysis, class_name, class_fields)
            
            # Show discovered values for debugging
            if query_analysis.get("field_value_discovery"):
                print(f"📋 Value Discovery Results:")
                for field, values_info in query_analysis["field_value_discovery"].items():
                    print(f"   {field}: {len(values_info['values'])} values, type: {values_info['field_type']}")
        else:
            print(f"⚡ Skipping value discovery for simple query - optimized for performance")
        
        # Step 4: Build smart OQL query based on analysis and discovered fields
        oql_query, validation_info = await build_smart_oql_query(class_name, query_analysis, class_fields)
        
        # Step 4.5: Handle value validation and multi-query scenarios
        if validation_info.get("has_unvalidated_filters", False):
            print(f"⚠️ Some filters need value discovery - running validation")
            # TODO: Implement value discovery for unvalidated filters
            # For now, we'll proceed without the unvalidated filters
            skipped_count = len(validation_info.get("skipped_filters", []))
            print(f"📊 Proceeding with {skipped_count} filters skipped due to lack of validation")
        
        # Handle multi-query scenarios (e.g., "closed vs open")
        if validation_info.get("needs_multi_query", False):
            comparison_values = validation_info.get("comparison_values", [])
            print(f"🔄 Executing multi-query for comparison: {comparison_values}")
            
            # Execute separate queries for each comparison value
            all_results = {}
            for value in comparison_values:
                # Create a modified query analysis with only this value
                value_query_analysis = query_analysis.copy()
                value_filters = []
                
                # Add this specific value filter
                for filter_info in query_analysis.get("discovered_filters", []):
                    if filter_info.get("is_comparison_value", False) and filter_info["value"] == value:
                        value_filters.append(filter_info)
                    elif not filter_info.get("is_comparison_value", False):
                        value_filters.append(filter_info)
                
                value_query_analysis["discovered_filters"] = value_filters
                value_oql_query, _ = await build_smart_oql_query(class_name, value_query_analysis, class_fields)
                
                # Execute this specific query
                value_operation_data = {
                    "operation": "core/get",
                    "class": class_name,
                    "key": value_oql_query,
                    "output_fields": determine_smart_output_fields(value_query_analysis, class_fields, output_format),
                    "limit": limit
                }
                
                value_result = await client.make_request(value_operation_data)
                
                if value_result.get("code") == 0:
                    value_objects = value_result.get("objects", {})
                    all_results[value] = {
                        "objects": value_objects,
                        "count": len(value_objects) if value_objects else 0,
                        "query": value_oql_query
                    }
                    print(f"✅ Query for '{value}': {len(value_objects) if value_objects else 0} results")
                else:
                    all_results[value] = {
                        "error": value_result.get("message", "Unknown error"),
                        "query": value_oql_query
                    }
                    print(f"❌ Query for '{value}' failed: {value_result.get('message', 'Unknown error')}")
            
            # Format multi-query results
            header = f"**🔄 Multi-Query Comparison Results**\n\n"
            header += f"**Query**: \"{query}\"\n"
            header += f"**Detected Class**: {class_name}\n"
            header += f"**Comparison Values**: {', '.join(comparison_values)}\n\n"
            
            content = ""
            for value, result_info in all_results.items():
                content += f"## {value.title()}\n"
                if "error" in result_info:
                    content += f"❌ Error: {result_info['error']}\n"
                    content += f"Query: `{result_info['query']}`\n\n"
                else:
                    objects = result_info["objects"]
                    count = result_info["count"]
                    content += f"**Count**: {count}\n"
                    content += f"**Query**: `{result_info['query']}`\n\n"
                    
                    if count > 0 and output_format != "summary":
                        content += _format_objects_output_smart(
                            objects, 
                            class_name, 
                            output_format, 
                            class_fields, 
                            [], 
                            result_info['query']
                        )
                    content += "\n"
            
            return header + content
        
        # Step 5: Determine optimal output fields based on query type and discovered schema (SMART SELECTION)
        output_fields = determine_smart_output_fields(query_analysis, class_fields, output_format)
        
        # Step 6: Determine output format (dynamic based on intent)
        if output_format == "auto":
            output_format = query_analysis.get("format_preference", "detailed")
        
        # Step 7: Execute the optimized query
        operation_data = {
            "operation": "core/get",
            "class": class_name,
            "key": oql_query,
            "output_fields": output_fields,
            "limit": limit
        }
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"❌ **Query Error**: {result.get('message', 'Unknown error')}"
            return f"❌ **Query Error**: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        if objects is None:
            objects = {}
        
        # Extract actual count from API response message
        actual_count = _extract_count_from_message(result.get("message", ""))
        returned_count = len(objects)
        
        # Debug: Show the actual message for troubleshooting
        debug_msg = result.get("message", "")
        if debug_msg:
            print(f"🔍 DEBUG - API Response Message: '{debug_msg}'")
            print(f"🔍 DEBUG - Extracted Count: {actual_count}")
            print(f"🔍 DEBUG - Returned Count: {returned_count}")
        
        # Step 8: Build intelligent response header with schema info
        header = f"**🚀 Smart Query Results**\n\n"
        header += f"**Operation Data**: {json.dumps(operation_data, indent=2)}\n"
        header += f"**Query**: \"{query}\"\n"
        header += f"**Detected Class**: {class_name} (confidence: {confidence:.1%})\n"
        header += f"**Action**: {query_analysis.get('action', 'list').title()}\n"
        header += f"**Query Complexity**: {query_complexity['complexity'].title()}\n"
        
        # Show schema discovery info
        header += f"**Schema Discovery**: Found {class_fields.get('total_fields', 0)} total fields\n"
        header += f"**Key Fields Used**: {', '.join(class_fields.get('key_fields', []))}\n"
        
        # Show intelligent value discovery info
        if query_complexity['needs_value_discovery'] and query_analysis.get('field_value_discovery'):
            discovered_fields = list(query_analysis['field_value_discovery'].keys())
            header += f"**Value Discovery**: Analyzed {len(discovered_fields)} field(s): {', '.join(discovered_fields)}\n"
        elif query_complexity['complexity'] == 'simple':
            header += f"**Value Discovery**: Skipped for performance (simple query)\n"
        
        # Show discovered filters if any
        discovered_filters = query_analysis.get("discovered_filters", [])
        if discovered_filters:
            header += f"**Schema-Aware Filters**: {len(discovered_filters)} applied\n"
            for filter_info in discovered_filters:
                header += f"  - {filter_info['field']} {filter_info['operator']} {filter_info['value']}\n"
        
        # Always show count information in the main output for API consumption
        if actual_count is not None and actual_count > 0:
            header += f"**Total Records Found**: {actual_count}\n"
            header += f"**Records Returned**: {returned_count}\n"
        else:
            header += f"**Total Records Found**: Not available\n"
            header += f"**Records Returned**: {returned_count}\n"
            
        header += f"**Output Fields**: {output_fields}\n\n"
        header += "---\n\n"
        
        if not objects:
            if actual_count is not None and actual_count > 0:
                return header + f"Found {actual_count} {class_name} object(s) but none returned (possibly due to access restrictions or filters)."
            else:
                # INTELLIGENT FALLBACK: When 0 results and we have filters, try to find better values
                discovered_filters = query_analysis.get("discovered_filters", [])
                if discovered_filters and not query_complexity.get('needs_value_discovery', False):
                    # Only for queries that didn't already do value discovery
                    fallback_header = header + f"🔍 **No results found. Checking for better field value matches...**\n\n"
                    
                    # Try to find better values for each filter
                    suggested_fixes = []
                    for filter_info in discovered_filters:
                        field = filter_info.get("field")
                        original_value = filter_info.get("value")
                        
                        if field and original_value:
                            # Discover actual values for this field
                            field_values = await discover_field_values(class_name, field, limit=100)
                            
                            if field_values["values"]:
                                # Try to find a better match
                                best_match = find_best_value_match(original_value, field_values["values"])
                                
                                if best_match != original_value:
                                    suggested_fixes.append({
                                        "field": field,
                                        "original": original_value,
                                        "suggested": best_match,
                                        "all_values": field_values["values"][:10]  # Show first 10 available values
                                    })
                    
                    if suggested_fixes:
                        fallback_header += "**💡 Suggested fixes:**\n"
                        for fix in suggested_fixes:
                            fallback_header += f"- Field **{fix['field']}**: You searched for '{fix['original']}', did you mean '{fix['suggested']}'?\n"
                            fallback_header += f"  Available values: {', '.join(fix['all_values'])}\n"
                        
                        # Try the query with the first suggested fix
                        if suggested_fixes:
                            first_fix = suggested_fixes[0]
                            fallback_header += f"\n🔄 **Trying with suggested value '{first_fix['suggested']}'...**\n\n"
                            
                            # Build new OQL with corrected value
                            corrected_query = oql_query.replace(f"= '{first_fix['original']}'", f"= '{first_fix['suggested']}'")
                            
                            # Execute corrected query
                            corrected_operation = operation_data.copy()
                            corrected_operation["key"] = corrected_query
                            
                                                       
                            corrected_result = await client.make_request(corrected_operation)
                            
                            if corrected_result.get("code") == 0:
                                corrected_objects = corrected_result.get("objects", {})
                                if corrected_objects:
                                    fallback_header += f"✅ **Found {len(corrected_objects)} results with corrected value!**\n\n"
                                    
                                    # Format the corrected results
                                    corrected_formatted = _format_objects_output_smart(
                                        corrected_objects, 
                                        class_name, 
                                        output_format, 
                                        class_fields, 
                                        query_analysis.get("requested_fields", []), 
                                        corrected_query
                                    )
                                    
                                    return fallback_header + corrected_formatted
                    
                    return fallback_header + "❌ No better matches found. The query criteria may not match any existing data."
                
                # Standard no results message
                no_objects_msg = f"No {class_name} objects found matching your query."
                if actual_count is None:
                    no_objects_msg += " (Total count not available - this could mean no objects exist or access restrictions apply.)"
                return header + no_objects_msg
        
        # Step 9: Handle different action types with smart formatting
        if query_analysis.get("action") == "count":
            # For count queries, always show total count prominently
            if actual_count is not None and actual_count > 0:
                display_count = actual_count
                count_source = "from API message"
            else:
                display_count = returned_count
                count_source = "from returned objects"
            
            count_result = f"📊 **Count Result**: {display_count} {class_name} object(s) ({count_source})\n"
            count_result += f"**Total Count**: {actual_count if actual_count is not None else 'Not available'}\n"
            
            if query_analysis.get("grouping"):
                count_result += f"\n**Breakdown by {query_analysis['grouping']}:**\n"
                groups = {}
                for obj_data in objects.values():
                    if obj_data.get("code") == 0:
                        fields = obj_data.get("fields", {})
                        group_value = fields.get(query_analysis["grouping"], "Unknown")
                        groups[group_value] = groups.get(group_value, 0) + 1
                
                for group_name, count in sorted(groups.items()):
                    count_result += f"• {group_name}: {count}\n"
            
            return header + count_result
        
        
        
        # Step 10: Smart object formatting using discovered schema (NO FIELD LIMITS)
        formatted_output = _format_objects_output_smart(
            objects, 
            class_name, 
            output_format, 
            class_fields, 
            query_analysis.get("requested_fields", []), 
            oql_query
        )
        
        # Add available fields summary (show more fields now)
        if class_fields.get("field_names") and output_format == "detailed":
            footer = f"\n\n💡 **Available Fields in {class_name}**:\n"
            sample_fields = class_fields.get("field_names", [])[:20]  # Increased from 10 to 20
            for field in sample_fields:
                sample_val = class_fields.get("sample_values", {}).get(field, "")
                if sample_val:
                    footer += f"- **{field}**: {sample_val}\n"
                else:
                    footer += f"- **{field}**\n"
            if len(class_fields.get("field_names", [])) > 20:
                footer += f"...and {len(class_fields.get('field_names', [])) - 20} more fields...\n"
            footer += f"**Total**: {class_fields.get('total_fields', 0)} fields available"
            formatted_output += footer
        
        return header + formatted_output
        
    except Exception as e:
        return f"❌ **Smart Query Error**: {str(e)}"

@mcp.tool()
async def discover_available_classes(search_term: Optional[str] = None) -> str:
    """
    Discover available iTop classes with their descriptions and use cases.
    
    Args:
        search_term: Optional term to filter classes by (e.g., "ticket", "server", "user")
    """
    try:
        result = "📚 **iTop Class Discovery**\n\n"
        result = "📚 **iTop Class Discovery**\n\n"
        
        if search_term:
            result += f"🔍 **Searching for**: \"{search_term}\"\n\n"
            search_lower = search_term.lower()
        else:
            result += "📋 **All Available Classes by Category**\n\n"
        if search_term:
            result += f"🔍 **Searching for**: \"{search_term}\"\n\n"
            search_lower = search_term.lower()
        else:
            result += "📋 **All Available Classes by Category**\n\n"
        
        total_classes = 0
        
        for category_name, category_list in ITOP_CLASS_TAXONOMY.items():
            category_header_added = False
            
            for use_case in category_list:
                use_case_header_added = False
                matching_classes = []
                
                for class_name in use_case["classes"]:
                    # Filter by search term if provided
                    if search_term:
                        if (search_lower in class_name.lower() or 
                            search_lower in use_case["description"].lower() or
                            any(search_lower in keyword for keyword in use_case.get("keywords", []))):
                            matching_classes.append(class_name)
                    else:
                        matching_classes.append(class_name)
                
                if matching_classes:
                    if not category_header_added:
                        result += f"## {category_name.replace('And', ' & ')}\n\n"
                        category_header_added = True
                    
                    if not use_case_header_added:
                        result += f"### 🏷️ {use_case['name']}\n"
                        result += f"*{use_case['description']}*\n\n"
                        use_case_header_added = True
                    
                    result += f"**Classes**: {', '.join(matching_classes)}\n"
                    if use_case.get("keywords"):
                        result += f"**Keywords**: {', '.join(use_case['keywords'][:8])}\n"
                    result += "\n"
                    
                    total_classes += len(matching_classes)
        
        if search_term and total_classes == 0:
            result += f"❌ No classes found matching '{search_term}'\n\n"
            result += "💡 **Try searching for**: ticket, server, pc, user, organization, change\n"
        else:
            result += f"📊 **Total Classes**: {total_classes}\n\n"
        
        result += "💡 **Usage Tips**:\n"
        result += "• Use `smart_query_processor()` with natural language\n"
        result += "• Example: \"Show me all servers\" or \"Count tickets by status\"\n"
        result += "• The system will auto-detect the best class to use\n"
        
        return result
        
    except Exception as e:
        return f"Error discovering classes: {str(e)}"
def _extract_count_from_message(message: str) -> int:
    """Extract count from API response message with flexible pattern matching."""
    try:
        import re
        
        if not message:
            return 0
        
        message_lower = message.lower()
        
        # Try multiple flexible patterns in order of preference
        patterns = [
            # iTop common formats
            r'found[:\s]*(\d+)',                    # "Found: 92", "Found 92", "found:92"
            r'(\d+)\s*found',                       # "92 found", "92found"
            r'(\d+)\s*objects?\s*found',            # "92 objects found", "1 object found"
            r'found\s*(\d+)\s*objects?',            # "found 92 objects", "found 1 object"
            r'(\d+)\s*objects?\s*returned',         # "92 objects returned"
            r'returned\s*(\d+)\s*objects?',         # "returned 92 objects"
            r'(\d+)\s*results?',                    # "92 results", "1 result"
            r'results?\s*[:\s]*(\d+)',              # "results: 92", "results 92"
            r'total[:\s]*(\d+)',                    # "total: 92", "total 92"
            r'count[:\s]*(\d+)',                    # "count: 92", "count 92"
            r'(\d+)\s*records?',                    # "92 records", "1 record"
            r'records?\s*[:\s]*(\d+)',              # "records: 92"
            r'(\d+)\s*entries',                     # "92 entries"
            r'entries[:\s]*(\d+)',                  # "entries: 92"
            # Generic number extraction as last resort
            r'(\d+)'                                # Any number in the message
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                count = int(match.group(1))
                # Sanity check: reasonable count range
                if 0 <= count <= 1000000:  # Up to 1M records seems reasonable
                    return count
        
        return 0
    except (ValueError, AttributeError):
        return 0


def main():
    """Main entry point for the MCP server"""
    # Check environment variables
    if not all([ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD]):
        print("Error: Missing required environment variables:")
        print("  - ITOP_BASE_URL: URL to your iTop instance")
        print("  - ITOP_USER: iTop username")  
        print("  - ITOP_PASSWORD: iTop password")
        print("  - ITOP_VERSION: API version (optional, default: 1.4)")
        exit(1)
    
    # Run the server
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()

