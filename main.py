#!/usr/bin/env python3
"""
iTop MCP Server

A Model Context Protocol server for interacting with iTop ITSM system via REST API.
Provides tools for managing tickets, CIs, and other iTop objects.
"""

import asyncio
import base64
import json
import os
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

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
    
    async def _make_request(self, operation_data: dict) -> dict:
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
                raise Exception(f"Request failed: {e}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON response: {e}")


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
        result = await client._make_request(operation_data)
        
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
async def get_objects(class_name: str, key: Optional[str] = None, output_fields: str = "*") -> str:
    """
    Get objects from iTop.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Person, Organization)
        key: Optional search criteria. Can be an ID, OQL query, or JSON search criteria
        output_fields: Comma-separated list of fields to return, or "*" for all fields
    """
    try:
        client = get_itop_client()
        
        operation_data = {
            "operation": "core/get",
            "class": class_name,
            "output_fields": output_fields
        }
        
        if key:
            # Try to parse as JSON first, then treat as string
            try:
                operation_data["key"] = json.loads(key)
            except json.JSONDecodeError:
                operation_data["key"] = key
        
        result = await client._make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects")
        if not objects:
            return f"No {class_name} objects found."
        
        output = f"Found {len(objects)} {class_name} object(s):\n\n"
        
        for obj_key, obj_data in objects.items():
            if obj_data.get("code") == 0:
                fields = obj_data.get("fields", {})
                output += f"--- {obj_key} ---\n"
                for field, value in fields.items():
                    output += f"{field}: {value}\n"
                output += "\n"
            else:
                output += f"Error with {obj_key}: {obj_data.get('message', 'Unknown error')}\n\n"
        
        return output
    except Exception as e:
        return f"Error getting objects: {str(e)}"


@mcp.tool()
async def create_object(class_name: str, fields_json: str, comment: str = "") -> str:
    """
    Create a new object in iTop.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Person, Organization)
        fields_json: JSON string containing the object fields and values
        comment: Optional comment for the operation
    """
    try:
        client = get_itop_client()
        
        try:
            fields = json.loads(fields_json)
        except json.JSONDecodeError:
            return "Error: fields_json must be valid JSON"
        
        operation_data = {
            "operation": "core/create",
            "class": class_name,
            "fields": fields,
            "output_fields": "*"
        }
        
        if comment:
            operation_data["comment"] = comment
        
        result = await client._make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        objects = result.get("objects", {})
        if objects:
            obj_key, obj_data = next(iter(objects.items()))
            if obj_data.get("code") == 0:
                return f"Successfully created {class_name} with key: {obj_data.get('key')}\nObject: {obj_key}"
            else:
                return f"Error creating object: {obj_data.get('message', 'Unknown error')}"
        else:
            return "Object created but no details returned"
    except Exception as e:
        return f"Error creating object: {str(e)}"


@mcp.tool()
async def update_object(class_name: str, key: str, fields_json: str, comment: str = "") -> str:
    """
    Update an existing object in iTop.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Person, Organization)
        key: Object identifier (ID, OQL query, or JSON search criteria)
        fields_json: JSON string containing the fields to update
        comment: Optional comment for the operation
    """
    try:
        client = get_itop_client()
        
        try:
            fields = json.loads(fields_json)
        except json.JSONDecodeError:
            return "Error: fields_json must be valid JSON"
        
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
        
        result = await client._make_request(operation_data)
        
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
        
        result = await client._make_request(operation_data)
        
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
async def apply_stimulus(class_name: str, key: str, stimulus: str, fields_json: str = "{}", comment: str = "") -> str:
    """
    Apply a stimulus to change the state of an iTop object.
    
    Args:
        class_name: The iTop class name (e.g., UserRequest, Incident)
        key: Object identifier (ID, OQL query, or JSON search criteria)
        stimulus: The stimulus to apply (e.g., ev_assign, ev_resolve, ev_close)
        fields_json: JSON string containing any additional fields to set
        comment: Optional comment for the operation
    """
    try:
        client = get_itop_client()
        
        try:
            fields = json.loads(fields_json)
        except json.JSONDecodeError:
            return "Error: fields_json must be valid JSON"
        
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
        
        result = await client._make_request(operation_data)
        
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
        
        result = await client._make_request(operation_data)
        
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
        
        result = await client._make_request(operation_data)
        
        if result.get("code") != 0:
            return f"Error: {result.get('message', 'Unknown error')}"
        
        authorized = result.get("authorized", False)
        if authorized:
            return f"✅ Credentials are valid for user: {client.username}"
        else:
            return f"❌ Invalid credentials for user: {client.username}"
    except Exception as e:
        return f"Error checking credentials: {str(e)}"


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
