# iTop MCP Server

A Model Context Protocol (MCP) server for integrating with iTop ITSM (IT Service Management) systems. This server provides AI assistants with the ability to interact with iTop through its REST API, enabling operations like ticket management, CI (Configuration Item) management, and more.

## Features

The iTop MCP server provides the following tools:

- **list_operations**: List all available iTop REST API operations
- **get_objects**: Search and retrieve iTop objects (tickets, users, CIs, etc.)
- **create_object**: Create new objects in iTop
- **update_object**: Update existing objects
- **delete_object**: Delete objects (with simulation mode for safety)
- **apply_stimulus**: Apply state transitions to objects (e.g., resolve tickets)
- **get_related_objects**: Find related objects through impact/dependency relationships
- **check_credentials**: Verify iTop API credentials

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
# Install the package
pip install itop-mcp

# Or using uv
uv add itop-mcp
```

### Option 2: Install from Source

1. **Prerequisites**:
   - Python 3.10 or higher
   - Access to an iTop instance with REST API enabled
   - iTop user account with "REST Services User" profile

2. **Install dependencies**:
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Clone and install
   git clone https://github.com/roneydsilva/itop-mcp.git
   cd itop-mcp
   uv sync
   ```

3. **Configure iTop connection**:
   ```bash
   # Copy the example configuration
   cp .env.example .env
   
   # Edit the .env file with your iTop details
   nano .env
   ```

   Required environment variables:
   - `ITOP_BASE_URL`: Your iTop instance URL (e.g., https://itop.yourcompany.com)
   - `ITOP_USER`: Username with REST Services User profile
   - `ITOP_PASSWORD`: Password for the user
   - `ITOP_VERSION`: API version (optional, default: 1.4)

## Usage

### Running the Server

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the server
uv run main.py
```

### Connecting to Claude Desktop

#### Option 1: Using PyPI Installation

To use this server with Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "itop": {
      "command": "itop-mcp",
      "env": {
        "ITOP_BASE_URL": "https://your-itop-instance.com",
        "ITOP_USER": "your_username",
        "ITOP_PASSWORD": "your_password"
      }
    }
  }
}
```

#### Option 2: Using Source Installation

```json
{
  "mcpServers": {
    "itop": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/itop-mcp",
        "run",
        "main.py"
      ],
      "env": {
        "ITOP_BASE_URL": "https://your-itop-instance.com",
        "ITOP_USER": "your_username",
        "ITOP_PASSWORD": "your_password"
      }
    }
  }
}
```

### Example Operations

Once connected, you can ask your AI assistant to perform operations like:

- "List all open user requests in iTop"
- "Create a new incident ticket for server downtime"
- "Find all CIs related to the mail server"
- "Update the priority of ticket #123 to high"
- "Resolve ticket #456 with resolution details"

## iTop Class Examples

Common iTop classes you can work with:

- **UserRequest**: User requests/tickets
- **Incident**: Incident tickets
- **Person**: Users and contacts
- **Organization**: Organizations/companies
- **Server**: Server configuration items
- **Application**: Application configuration items
- **Service**: IT services
- **Contract**: Contracts and SLAs

## Security Notes

- Always use HTTPS for your iTop instance in production
- Store credentials securely (use environment variables, not hardcoded values)
- The user account should have minimal necessary permissions
- Test operations in a development environment first
- Use simulation mode for delete operations until you're confident

## Troubleshooting

### Common Issues

1. **Authentication errors**: Ensure your user has the "REST Services User" profile in iTop
2. **Connection errors**: Verify the ITOP_BASE_URL is correct and accessible
3. **Permission errors**: Check that the user has appropriate rights on the objects you're trying to access

### Testing the Connection

Use the `check_credentials` tool to verify your configuration:

```python
# The server will automatically test credentials on startup
# You can also ask the AI assistant: "Check my iTop credentials"
```

## Development

To extend the server:

1. Add new tools by creating functions decorated with `@mcp.tool()`
2. Follow the iTop REST API documentation for available operations
3. Handle errors gracefully and provide informative messages
4. Test thoroughly in a development environment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. See the LICENSE file for details.

## References

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [iTop REST API Documentation](https://www.itophub.io/wiki/page?id=latest:advancedtopics:rest_json)
- [iTop Official Website](https://www.combodo.com/itop)