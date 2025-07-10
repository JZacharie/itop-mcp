# Changelog

All notable changes to the iTop MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-07-10

### Added
- Smart Query Processor: Accepts natural language ITSM queries and maps them to iTop classes and fields automatically.
- Dynamic Schema Discovery: Automatically detects available iTop classes and their fields for flexible, schema-aware queries.
- Advanced Query Features: Supports grouping, filtering, SLA-based stats, and relationship navigation in natural language queries.
- Enhanced User-Facing Features: Added support for queries such as PC/Server/VM counts, status breakdowns, SLA compliance, and more.
- Extensibility: Framework for adding new query types and custom logic with minimal code changes.
- Improved Documentation: Comprehensive rewrite of README.md, including advanced usage, extensibility, and feature documentation.

### Changed
- README.md updated for clarity, completeness, and alignment with new features and usage patterns.

### Fixed
- Minor documentation and usage guide corrections.

## [1.0.0] - 2025-06-15

### Added
- Initial release of iTop MCP Server
- Complete Model Context Protocol server for iTop ITSM integration
- 8 comprehensive tools for iTop REST API operations:
  - `list_operations`: List available API operations
  - `get_objects`: Search and retrieve iTop objects  
  - `create_object`: Create new tickets/CIs/users
  - `update_object`: Update existing objects
  - `delete_object`: Safe deletion with simulation mode
  - `apply_stimulus`: Apply state transitions
  - `get_related_objects`: Find dependencies/impacts
  - `check_credentials`: Validate API access
- Full CRUD support (create, read, update, delete)
- State management with stimulus application
- Relationship discovery and impact analysis
- Comprehensive error handling and validation
- Safety features (simulation mode for deletions)
- Complete documentation (README, USAGE guide, PUBLISHING guide)
- Development tools (Makefile, test scripts)
- Configuration templates
- Claude Desktop integration examples
- MIT License
- PyPI publishing configuration
- Production-ready error handling

### Technical Features
- FastMCP framework for MCP protocol
- httpx for async HTTP requests
- Comprehensive type hints and documentation
- Environment-based configuration
- Python 3.10+ support

### Documentation
- Comprehensive README with installation and usage
- Detailed USAGE guide with examples
- Publishing guide for maintainers
- Project summary and architecture overview
- Configuration templates for easy setup

[1.0.0]: https://github.com/roneydsilva/itop-mcp/releases/tag/v1.0.0
