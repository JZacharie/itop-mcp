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


def _format_objects_output(objects: dict, class_name: str, format_type: str, search_key: Optional[str] = None) -> str:
    """Helper function to format object output in different styles."""
    
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
        # Summary format - just key information
        output = header
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                name = fields.get("friendlyname") or fields.get("name") or fields.get("title") or "No name"
                status = fields.get("status", "")
                status_text = f" ({status})" if status else ""
                output += f"• {obj_key}: {name}{status_text}\n"
        return output
    
    elif format_type == "table":
        # Table format for better readability
        output = header
        
        # Determine common fields across all objects
        all_fields = set()
        valid_objects = []
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                all_fields.update(fields.keys())
                valid_objects.append((obj_key, fields))
        
        # Prioritize important fields
        priority_fields = ["friendlyname", "name", "title", "status", "id"]
        display_fields = [f for f in priority_fields if f in all_fields]
        
        # Add other fields (up to 3 more to keep table readable)
        other_fields = [f for f in sorted(all_fields) if f not in display_fields][:3]
        display_fields.extend(other_fields)
        
        if not display_fields:
            return f"{header}No displayable fields found."
        
        # Create table header
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
            for field in display_fields:
                value = str(fields.get(field, "")).replace("\n", " ")[:col_widths[field]-2]
                row += f"{value:<{col_widths[field]}} | "
            output += row.rstrip(" |") + "\n"
        
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


def _format_field_value(value: Any) -> str:
    """Helper function to format field values for display."""
    if value is None:
        return "None"
    
    str_value = str(value)
    
    # Handle HTML content
    if "<" in str_value and ">" in str_value:
        # Simple HTML tag removal for cleaner display
        str_value = re.sub(r'<[^>]+>', '', str_value).strip()
    
    # Truncate very long values
    if len(str_value) > 150:
        str_value = str_value[:150] + "..."
    
    # Replace newlines with spaces for single-line display
    str_value = str_value.replace("\n", " ").replace("\r", "")
    
    return str_value


@mcp.tool()
async def create_object(class_name: str, fields_json, comment: str = "") -> str:
    """
    Create a new object in iTop.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Person, Organization)
        fields_json: JSON string or dict containing the object fields and values
        comment: Optional comment for the operation
    """
    try:
        client = get_itop_client()
        
        # Handle both string and dict inputs (MCP client sometimes sends dict)
        if isinstance(fields_json, str):
            try:
                fields = json.loads(fields_json)
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON in fields_json parameter: {e}"
        elif isinstance(fields_json, dict):
            # MCP client passed a dict directly
            fields = fields_json
        else:
            return f"Error: fields_json must be a JSON string or dict, got {type(fields_json)}"
        
        operation_data = {
            "operation": "core/create",
            "class": class_name,
            "fields": fields,
            "output_fields": "*"
        }
        
        if comment:
            operation_data["comment"] = comment
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        if objects:
            obj_key, obj_data = next(iter(objects.items()))
            if obj_data.get("code") == 0:
                created_id = obj_data.get("key")
                fields_info = obj_data.get("fields", {})
                friendly_name = fields_info.get("friendlyname", obj_key)
                
                output = f"✅ **{class_name} created successfully!**\n\n"
                output += f"🔑 **Object Key:** {obj_key}\n"
                output += f"🆔 **ID:** {created_id}\n"
                if friendly_name != obj_key:
                    output += f"📋 **Name:** {friendly_name}\n"
                
                # Show key fields that were set
                key_fields = ["name", "title", "status", "code"]
                for field in key_fields:
                    if field in fields_info and fields_info[field]:
                        output += f"📝 **{field.title()}:** {fields_info[field]}\n"
                
                return output
            else:
                return f"Error creating object: {obj_data.get('message', 'Unknown error')}"
        else:
            return "Object created but no details returned"
    except Exception as e:
        return f"Error creating object: {str(e)}"


@mcp.tool()
async def update_object(class_name: str, key: str, fields_json, comment: str = "") -> str:
    """
    Update an existing object in iTop.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Person, Organization)
        key: Object identifier (ID, OQL query, or JSON search criteria)
        fields_json: JSON string or dict containing the fields to update
        comment: Optional comment for the operation
    """
    try:
        client = get_itop_client()
        
        # Handle both string and dict inputs
        if isinstance(fields_json, str):
            try:
                fields = json.loads(fields_json)
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON in fields_json parameter: {e}"
        elif isinstance(fields_json, dict):
            fields = fields_json
        else:
            return f"Error: fields_json must be a JSON string or dict, got {type(fields_json)}"
        
        # Try to parse key as JSON, otherwise use as string
        try:
            parsed_key = json.loads(key)
        except json.JSONDecodeError:
            parsed_key = key
        
        operation_data = {
            "operation": "core/update",
            "class": class_name,
            "key": parsed_key,
            "fields": fields,
            "output_fields": "*"
        }
        
        if comment:
            operation_data["comment"] = comment
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        if objects:
            obj_key, obj_data = next(iter(objects.items()))
            if obj_data.get("code") == 0:
                return f"Successfully updated {class_name}: {obj_key}"
            else:
                return f"Error updating object: {obj_data.get('message', 'Unknown error')}"
        else:
            return "Object updated but no details returned"
    except Exception as e:
        return f"Error updating object: {str(e)}"


@mcp.tool()
async def delete_object(class_name: str, key: str, simulate: bool = True, comment: str = "") -> str:
    """
    Delete object(s) from iTop.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Person, Organization)
        key: Object identifier (ID, OQL query, or JSON search criteria)
        simulate: If True, only simulate the deletion (default: True for safety)
        comment: Optional comment for the operation
    """
    try:
        client = get_itop_client()
        
        # Try to parse key as JSON, otherwise use as string
        try:
            parsed_key = json.loads(key)
        except json.JSONDecodeError:
            parsed_key = key
        
        operation_data = {
            "operation": "core/delete",
            "class": class_name,
            "key": parsed_key,
            "simulate": simulate
        }
        
        if comment:
            operation_data["comment"] = comment
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        if simulate:
            output = "SIMULATION MODE - No actual deletion performed\n\n"
        else:
            output = "DELETION PERFORMED\n\n"
        
        objects = result.get("objects", {})
        for obj_key, obj_data in objects.items():
            status_code = obj_data.get("deletion", {}).get("status", "unknown")
            status_msg = obj_data.get("deletion", {}).get("message", "")
            output += f"{obj_key}: Status {status_code} - {status_msg}\n"
        
        return output
    except Exception as e:
        return f"Error deleting object: {str(e)}"


@mcp.tool()
async def apply_stimulus(class_name: str, key: str, stimulus: str, fields_json="{}", comment: str = "") -> str:
    """
    Apply a stimulus to change the state of an iTop object.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Incident)
        key: Object identifier (ID, OQL query, or JSON search criteria)
        stimulus: The stimulus to apply (e.g., ev_assign, ev_resolve, ev_close)
        fields_json: JSON string or dict containing any additional fields to set
        comment: Optional comment for the operation
    """
    try:
        client = get_itop_client()
        
        # Handle both string and dict inputs
        if isinstance(fields_json, str):
            try:
                fields = json.loads(fields_json)
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON in fields_json parameter: {e}"
        elif isinstance(fields_json, dict):
            fields = fields_json
        else:
            return f"Error: fields_json must be a JSON string or dict, got {type(fields_json)}"
        
        # Try to parse key as JSON, otherwise use as string
        try:
            parsed_key = json.loads(key)
        except json.JSONDecodeError:
            parsed_key = key
        
        operation_data = {
            "operation": "core/apply_stimulus",
            "class": class_name,
            "key": parsed_key,
            "stimulus": stimulus,
            "fields": fields,
            "output_fields": "*"
        }
        
        if comment:
            operation_data["comment"] = comment
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        if objects:
            obj_key, obj_data = next(iter(objects.items()))
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                status = fields.get("status", "unknown")
                return f"Successfully applied stimulus '{stimulus}' to {class_name}: {obj_key}\nNew status: {status}"
            else:
                return f"Error applying stimulus: {obj_data.get('message', 'Unknown error')}"
        else:
            return "Stimulus applied but no details returned"
    except Exception as e:
        return f"Error applying stimulus: {str(e)}"


@mcp.tool()
async def get_related_objects(class_name: str, key: str, relation: str = "impacts", depth: int = 1, direction: str = "down") -> str:
    """
    Get objects related to the specified object through impact/dependency relationships.
    
    Args:
        class_name: The iTop class name (e.g., Server, Application, Service)
        key: Object identifier (ID, OQL query, or JSON search criteria)
        relation: Type of relation ("impacts" or "depends on")
        depth: Maximum depth for the search (default: 1)
        direction: Direction of the search ("up" or "down")
    """
    try:
        client = get_itop_client()
        
        # Try to parse key as JSON, otherwise use as string
        try:
            parsed_key = json.loads(key)
        except json.JSONDecodeError:
            parsed_key = key
        
        operation_data = {
            "operation": "core/get_related",
            "class": class_name,
            "key": parsed_key,
            "relation": relation,
            "depth": depth,
            "direction": direction
        }
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        relations = result.get("relations", {})
        
        if not objects:
            return f"No related objects found for {class_name} with relation '{relation}'"
        
        output = f"Related objects ({relation}, depth={depth}, direction={direction}):\n\n"
        output += f"Found {len(objects)} related object(s)\n\n"
        
        # Show objects
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                friendly_name = fields.get("friendlyname", obj_key)
                output += f"• {friendly_name} ({obj_key})\n"
            else:
                output += f"• Error with {obj_key}: {obj_data.get('message', 'Unknown error')}\n"
        
        # Show relationships if available
        if relations:
            output += "\nRelationships:\n"
            for origin, destinations in relations.items():
                output += f"{origin} relates to:\n"
                for dest in destinations:
                    output += f"  → {dest.get('key', 'unknown')}\n"
        
        return output
    except Exception as e:
        return f"Error getting related objects: {str(e)}"


@mcp.tool()
async def check_credentials() -> str:
    """Check if the configured iTop credentials are valid."""
    try:
        client = get_itop_client()
        operation_data = {
            "operation": "core/check_credentials",
            "user": client.username,
            "password": client.password
        }
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        authorized = result.get("authorized", False)
        if authorized:
            return f"✅ Credentials are valid for user: {client.username}"
        else:
            return f"❌ Invalid credentials for user: {client.username}"
    except Exception as e:
        return f"Error checking credentials: {str(e)}"


@mcp.tool()
async def get_ticket_details(ticket_ref: str, ticket_type: str = "UserRequest") -> str:
    """
    Get detailed information about a specific ticket.
    
    Args:
        ticket_ref: Ticket reference (e.g., R-000123) or ID
        ticket_type: Type of ticket (UserRequest, Incident, etc.)
    """
    try:
        client = get_itop_client()
        
        operation_data = {
            "operation": "core/get",
            "class": ticket_type,
            "key": ticket_ref,
            "output_fields": "*"
        }
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects")
        if not objects:
            return f"Ticket {ticket_ref} not found."
        
        obj_key, obj_data = next(iter(objects.items()))
        
        if obj_data.get("code") != 0:
            return f"Error retrieving ticket: {obj_data.get('message', 'Unknown error')}"
        
        fields = obj_data.get("fields", {})
        
        output = f"🎫 **Ticket Details: {obj_key}**\n\n"
        
        # Key information first
        key_fields = [
            ("Title", "title"),
            ("Status", "status"),
            ("Priority", "priority"),
            ("Urgency", "urgency"),
            ("Impact", "impact"),
            ("Caller", "caller_name"),
            ("Agent", "agent_name"),
            ("Team", "team_name"),
            ("Organization", "org_name"),
            ("Service", "service_name"),
            ("Creation Date", "creation_date"),
            ("Last Update", "last_update"),
            ("Resolution Date", "resolution_date"),
        ]
        
        for label, field in key_fields:
            value = fields.get(field, "")
            if value:
                output += f"**{label}:** {value}\n"
        
        # Description and solution
        description = fields.get("description", "")
        if description:
            output += f"\n**Description:**\n{description}\n"
        
        solution = fields.get("solution", "")
        if solution:
            output += f"\n**Solution:**\n{solution}\n"
        
        # Other fields
        output += f"\n**Other Information:**\n"
        excluded_fields = {field for _, field in key_fields} | {"description", "solution"}
        
        for field, value in fields.items():
            if field not in excluded_fields and value:
                # Format field name
                formatted_field = field.replace("_", " ").title()
                output += f"- {formatted_field}: {value}\n"
        
        return output
    except Exception as e:
        return f"Error getting ticket details: {str(e)}"


@mcp.tool()
async def get_organizations(name_filter: Optional[str] = None, limit: int = 20) -> str:
    """
    Get organizations from iTop.
    
    Args:
        name_filter: Optional name filter to search for specific organizations
        limit: Maximum number of organizations to return (default: 20)
    """
    try:
        client = get_itop_client()
        
        if name_filter:
            oql_query = f"SELECT Organization WHERE name LIKE '%{name_filter}%'"
            operation_data = {
                "operation": "core/get",
                "key": oql_query,
                "output_fields": "id,name,code,status,website,phone",
                "limit": limit
            }
        else:
            operation_data = {
                "operation": "core/get",
                "class": "Organization",
                "output_fields": "id,name,code,status,website,phone",
                "limit": limit
            }
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects")
        if not objects:
            filter_text = f" matching '{name_filter}'" if name_filter else ""
            return f"No organizations found{filter_text}."
        
        filter_text = f" matching '{name_filter}'" if name_filter else ""
        output = f"Found {len(objects)} organization(s){filter_text}:\n\n"
        
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                name = fields.get("name", "No name")
                code = fields.get("code", "")
                status = fields.get("status", "Unknown")
                website = fields.get("website", "")
                phone = fields.get("phone", "")
                
                output += f"🏢 **{obj_key}** - {name}\n"
                if code:
                    output += f"   📋 Code: {code}\n"
                output += f"   📊 Status: {status}\n"
                if website:
                    output += f"   🌐 Website: {website}\n"
                if phone:
                    output += f"   📞 Phone: {phone}\n"
                output += "\n"
        
        return output
    except Exception as e:
        return f"Error getting organizations: {str(e)}"


@mcp.tool()
async def create_user_request(title: str, description: str, caller_name: str, organization: Optional[str] = None, service: Optional[str] = None, impact: str = "3", urgency: str = "3") -> str:
    """
    Create a new user request ticket with better validation and defaults.
    
    Args:
        title: Title of the user request
        description: Detailed description of the issue
        caller_name: Name of the person reporting the issue
        organization: Organization name (optional)
        service: Service affected (optional) 
        impact: Impact level (1=High, 2=Medium, 3=Low, default: 3)
        urgency: Urgency level (1=High, 2=Medium, 3=Low, default: 3)
    """
    try:
        client = get_itop_client()
        
        # Build fields for the new ticket
        fields = {
            "title": title,
            "description": description,
            "impact": impact,
            "urgency": urgency
        }
        
        # Try to find the caller by name
        if caller_name:
            caller_search = {
                "operation": "core/get",
                "key": f"SELECT Person WHERE name LIKE '%{caller_name}%' OR first_name LIKE '%{caller_name}%'",
                "output_fields": "id,name,first_name,org_id",
                "limit": 1
            }
            
            caller_result = await client.make_request(caller_search)
            if caller_result.get("code") == 0 and caller_result.get("objects"):
                caller_obj_key = next(iter(caller_result["objects"].keys()))
                caller_obj = caller_result["objects"][caller_obj_key]
                if caller_obj.get("code") == 0:
                    # Extract ID from the key (format is usually "Person::123")
                    if "::" in caller_obj_key:
                        fields["caller_id"] = caller_obj_key.split("::")[1]
                    else:
                        fields["caller_id"] = caller_obj_key
                    caller_fields = caller_obj.get("fields", {})
                    if not organization and caller_fields.get("org_id"):
                        fields["org_id"] = caller_fields["org_id"]
        
        # Try to find organization if provided
        if organization and "org_id" not in fields:
            org_search = {
                "operation": "core/get", 
                "key": f"SELECT Organization WHERE name LIKE '%{organization}%'",
                "output_fields": "id,name",
                "limit": 1
            }
            
            org_result = await client.make_request(org_search)
            if org_result.get("code") == 0 and org_result.get("objects"):
                org_obj_key = next(iter(org_result["objects"].keys()))
                org_obj = org_result["objects"][org_obj_key]
                if org_obj.get("code") == 0:
                    # Extract ID from the key (format is usually "Organization::123")
                    if "::" in org_obj_key:
                        fields["org_id"] = org_obj_key.split("::")[1]
                    else:
                        fields["org_id"] = org_obj_key
        
        # Try to find service if provided
        if service:
            service_search = {
                "operation": "core/get",
                "key": f"SELECT Service WHERE name LIKE '%{service}%'",
                "output_fields": "id,name",
                "limit": 1
            }
            
            service_result = await client.make_request(service_search)
            if service_result.get("code") == 0 and service_result.get("objects"):
                service_obj_key = next(iter(service_result["objects"].keys()))
                service_obj = service_result["objects"][service_obj_key]
                if service_obj.get("code") == 0:
                    # Extract ID from the key (format is usually "Service::123")
                    if "::" in service_obj_key:
                        fields["service_id"] = service_obj_key.split("::")[1]
                    else:
                        fields["service_id"] = service_obj_key
        
        # Create the ticket
        operation_data = {
            "operation": "core/create",
            "class": "UserRequest",
            "fields": fields,
            "output_fields": "id,friendlyname,title,status,caller_name,org_name"
        }
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error creating user request: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        if objects:
            obj_key, obj_data = next(iter(objects.items()))
            if obj_data.get("code") == 0:
                ticket_fields = obj_data.get("fields", {})
                ticket_ref = ticket_fields.get("friendlyname", obj_key)
                status = ticket_fields.get("status", "unknown")
                caller = ticket_fields.get("caller_name", caller_name)
                org = ticket_fields.get("org_name", organization or "Unknown")
                
                output = f"✅ **User request created successfully!**\n\n"
                output += f"🎫 **Ticket:** {ticket_ref}\n"
                output += f"📋 **Title:** {title}\n"
                output += f"📊 **Status:** {status}\n"
                output += f"👤 **Caller:** {caller}\n"
                output += f"🏢 **Organization:** {org}\n"
                output += f"📈 **Impact:** {impact} | **Urgency:** {urgency}\n"
                
                return output
            else:
                return f"Error creating user request: {obj_data.get('message', 'Unknown error')}"
        else:
            return "User request created but no details returned"
    except Exception as e:
        return f"Error creating user request: {str(e)}"


@mcp.tool()
async def create_organization(name: str, code: Optional[str] = None, status: str = "active", comment: str = "") -> str:
    """
    Create a new organization in iTop with simplified parameters.
    
    Args:
        name: Organization name (required)
        code: Organization code (optional)
        status: Organization status (default: active)
        comment: Optional comment for the operation
    """
    try:
        client = get_itop_client()
        
        # Build fields dictionary
        fields = {"name": name}
        if code:
            fields["code"] = code
        if status:
            fields["status"] = status
        
        operation_data = {
            "operation": "core/create",
            "class": "Organization",
            "fields": fields,
            "output_fields": "*"
        }
        
        if comment:
            operation_data["comment"] = comment
        
        result = await client.make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        if objects:
            obj_key, obj_data = next(iter(objects.items()))
            if obj_data.get("code") == 0:
                created_id = obj_data.get("key")
                fields_info = obj_data.get("fields", {})
                friendly_name = fields_info.get("friendlyname", obj_key)
                
                output = f"✅ **Organization created successfully!**\n\n"
                output += f"🔑 **Object Key:** {obj_key}\n"
                output += f"🆔 **ID:** {created_id}\n"
                output += f"📋 **Name:** {fields_info.get('name', name)}\n"
                if fields_info.get('code'):
                    output += f"📝 **Code:** {fields_info.get('code')}\n"
                output += f"📊 **Status:** {fields_info.get('status', status)}\n"
                
                return output
            else:
                return f"Error creating organization: {obj_data.get('message', 'Unknown error')}"
        else:
            return "Organization created but no details returned"
    except Exception as e:
        return f"Error creating organization: {str(e)}"


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
