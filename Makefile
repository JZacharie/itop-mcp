# Makefile for iTop MCP Server

.PHONY: help install test validate run clean setup-dev config status build publish publish-test

# Default target
help:
	@echo "iTop MCP Server - Available commands:"
	@echo ""
	@echo "  setup        - Initial setup (install dependencies)"
	@echo "  install      - Install dependencies only"
	@echo "  test         - Run tests (requires iTop configuration)"
	@echo "  validate     - Validate server structure (no iTop needed)"
	@echo "  run          - Run the MCP server"
	@echo "  clean        - Clean up generated files"
	@echo "  setup-dev    - Setup development environment"
	@echo ""
	@echo "Configuration:"
	@echo "  config       - Copy example config and show setup instructions"
	@echo ""
	@echo "Publishing:"
	@echo "  build        - Build package for distribution"
	@echo "  publish-test - Publish to TestPyPI"
	@echo "  publish      - Publish to PyPI"
	@echo ""

# Initial setup
setup: install config
	@echo "✅ Setup complete!"
	@echo "💡 Next steps:"
	@echo "   1. Edit .env with your iTop credentials"
	@echo "   2. Test connection: make test"
	@echo "   3. Add to Claude Desktop config"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	uv sync

# Validate server structure (no credentials needed)
validate:
	@echo "🔍 Validating server structure..."
	@python -c "import main, inspect; print('✅ Server validation passed'); print(f'🔧 Found {len([n for n,o in inspect.getmembers(main) if inspect.iscoroutinefunction(o) and not n.startswith(\"_\")])} tools')"

# Run tests (requires iTop configuration)
test:
	@echo "🧪 Running iTop connection tests..."
	@if [ ! -f .env ]; then echo "❌ .env file not found. Run 'make config' first."; exit 1; fi
	uv run test_itop.py

# Run the MCP server
run:
	@echo "🚀 Starting iTop MCP server..."
	@if [ ! -f .env ]; then echo "❌ .env file not found. Run 'make config' first."; exit 1; fi
	uv run main.py

# Copy example configuration
config:
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env from example..."; \
		cp .env.example .env; \
		echo "✅ .env created. Please edit it with your iTop credentials:"; \
		echo ""; \
		echo "  ITOP_BASE_URL=https://your-itop-instance.com"; \
		echo "  ITOP_USER=your_username"; \
		echo "  ITOP_PASSWORD=your_password"; \
		echo ""; \
	else \
		echo "⚠️  .env already exists"; \
	fi

# Development setup
setup-dev: install
	@echo "🛠️  Setting up development environment..."
	@echo "✅ Development setup complete"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	@echo "✅ Cleanup complete"

# Build package
build: clean
	@echo "📦 Building package..."
	uv build
	@echo "✅ Build complete"
	@echo "📄 Distribution files:"
	@ls -la dist/

# Publish to TestPyPI (for testing)
publish-test: build
	@echo "🚀 Publishing to TestPyPI..."
	@echo "⚠️  Make sure you have configured your TestPyPI credentials"
	@echo "💡 Set your token: export UV_PUBLISH_TOKEN=your-testpypi-token"
	UV_PUBLISH_URL=https://test.pypi.org/legacy/ uv publish dist/*
	@echo "✅ Published to TestPyPI"
	@echo "🔗 Check: https://test.pypi.org/project/itop-mcp/"

# Publish to PyPI (production)
publish: build
	@echo "🚀 Publishing to PyPI..."
	@echo "⚠️  Make sure you have configured your PyPI credentials"
	@echo "⚠️  This will publish to the LIVE PyPI repository!"
	@echo "💡 Set your token: export UV_PUBLISH_TOKEN=your-pypi-token"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	uv publish dist/*
	@echo "✅ Published to PyPI"
	@echo "🔗 Check: https://pypi.org/project/itop-mcp/"

# Show current status
status:
	@echo "📊 iTop MCP Server Status:"
	@echo ""
	@echo "Dependencies:"
	@if [ -d .venv ]; then echo "  ✅ Virtual environment exists"; else echo "  ❌ Virtual environment missing"; fi
	@echo ""
	@echo "Configuration:"
	@if [ -f .env ]; then echo "  ✅ .env file exists"; else echo "  ❌ .env file missing"; fi
	@echo ""
	@echo "Server validation:"
	@python -c "import main; print('  ✅ Server imports successfully')" 2>/dev/null || echo "  ❌ Server import failed"
