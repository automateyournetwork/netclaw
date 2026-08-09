# Contributing to Zabbix MCP Server

Thank you for your interest in contributing to the Zabbix MCP Server! This document provides guidelines and information for contributors.

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Issues

1. **Search existing issues** first to avoid duplicates
2. **Use the issue template** when creating new issues
3. **Provide detailed information** including:
   - Zabbix version
   - Python version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages or logs

### Suggesting Features

1. **Check existing feature requests** to avoid duplicates
2. **Describe the use case** and why the feature would be valuable
3. **Provide examples** of how the feature would be used
4. **Consider implementation complexity** and compatibility

### Contributing Code

#### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Git
- Access to a Zabbix server for testing

#### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork:**
   ```bash
   git clone https://github.com/mpeirone/zabbix-mcp-server.git
   cd zabbix-mcp-server
   ```
3. **Install dependencies:**
   ```bash
   uv sync
   ```
4. **Set up environment:**
```bash
cp config/.env.example .env
# Configure with your test Zabbix server
```

#### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** following the coding standards
3. **Test your changes:**
```bash
uv run python scripts/test_server.py
```
4. **Commit your changes:**
   ```bash
   git commit -m "Add: brief description of changes"
   ```

#### Coding Standards

- **Follow PEP 8** Python style guidelines
- **Use type hints** for function parameters and return values
- **Write docstrings** for all functions and classes
- **Keep functions focused** and single-purpose
- **Use meaningful variable names**
- **Add comments** for complex logic

#### Code Structure

- **Tool functions** should follow the pattern: `@mcp.tool()` decorator
- **Error handling** should be comprehensive and user-friendly
- **Read-only mode** must be respected for write operations
- **Response formatting** should use `format_response()` helper

#### Example Tool Function

```python
@mcp.tool()
def example_get(param1: str, param2: Optional[int] = None) -> str:
    """Get example data from Zabbix
    
    Args:
        param1: Required parameter description
        param2: Optional parameter description
        
    Returns:
        JSON string with example data
        
    Raises:
        ValueError: If required parameters are missing
    """
    client = get_zabbix_client()
    params = {"param1": param1}
    
    if param2 is not None:
        params["param2"] = param2
    
    result = client.example.get(**params)
    return format_response(result)
```

#### Testing

- **Test all new functionality** with a real Zabbix server
- **Verify read-only mode** works correctly
- **Test error conditions** and edge cases
- **Ensure backward compatibility**

#### Documentation

- **Update README.md** if adding new features
- **Add examples** for new tool functions
- **Include docstrings** for all new functions

### Pull Request Process

1. **Ensure your branch is up to date:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. **Push your changes:**
   ```bash
   git push origin feature/your-feature-name
   ```
3. **Create a pull request** with:
   - Clear title and description
   - Reference to related issues
   - List of changes made
   - Testing performed
   - Screenshots if applicable

#### Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] Feature works in both read-only and full modes

## Development Guidelines

### Adding New Zabbix API Methods

1. **Check Zabbix API documentation** for the method
2. **Follow existing patterns** in the codebase
3. **Add proper parameter validation**
4. **Include comprehensive docstrings**
5. **Test with different parameter combinations**

### Error Handling

- **Use specific exception types** when possible
- **Provide helpful error messages** to users
- **Log errors appropriately** for debugging
- **Handle network timeouts** and connection issues

### Security Considerations

- **Never log sensitive information** (passwords, tokens)
- **Validate all user inputs**
- **Respect read-only mode** restrictions
- **Use secure defaults**

## Release Process

1. **Update version** in `pyproject.toml`
2. **Create release tag** following semantic versioning
3. **Update documentation** as needed

## Getting Help

- **GitHub Discussions** for questions and ideas
- **GitHub Issues** for bugs and feature requests
- **Code review** for implementation feedback

## Recognition

Contributors will be recognized in:
- README.md acknowledgments
- Release notes
- GitHub contributors list

Thank you for contributing to the Zabbix MCP Server project!