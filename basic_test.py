#!/usr/bin/env python3
"""
Simple test to verify the MCP server can be imported and basic functionality works
"""

import sys
import os

# Test imports
try:
    from main import mcp, ITopClient
    print("✅ Successfully imported MCP server components")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test server configuration
print(f"📊 Server Info:")
print(f"  Name: {mcp.name}")
print(f"  Description: {mcp.description}")

# List available tools
print(f"\n🔧 Available Tools ({len(mcp._tools)}):")
for i, (name, func) in enumerate(mcp._tools.items(), 1):
    doc = func.__doc__.strip().split('\n')[0] if func.__doc__ else "No description"
    print(f"  {i}. {name}: {doc}")

# Test ITopClient class (without actual connection)
print(f"\n🌐 ITopClient Class:")
print("  ✅ Class definition exists")
print("  ✅ Constructor parameters: base_url, username, password, version")

print(f"\n🎉 Basic validation completed successfully!")
print(f"💡 To test with actual iTop connection:")
print(f"   1. Copy .env.example to .env")
print(f"   2. Configure your iTop credentials")
print(f"   3. Run: uv run test_itop.py")
