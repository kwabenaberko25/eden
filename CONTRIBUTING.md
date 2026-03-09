# Contributing to Eden

Thank you for your interest in contributing to Eden! 🌿

## Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/eden.git`
3. **Install** development dependencies:

```bash
pip install -e ".[dev]"
```

4. **Create a branch** for your feature or fix:

```bash
git checkout -b feature/my-feature
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

We use **Ruff** for linting and formatting:

```bash
ruff check eden/
ruff format eden/
```

### Project Structure

```
eden/
├── eden/              # Framework source code
│   ├── app.py         # Core Eden application
│   ├── routing.py     # Router and route registration
│   ├── middleware.py   # Built-in middleware
│   ├── db/            # ORM and database layer
│   ├── auth/          # Authentication system
│   └── ...
├── tests/             # Test suite
├── docs/              # Documentation (MkDocs)
└── pyproject.toml     # Project configuration
```

## Submitting Changes

1. **Write tests** for any new functionality
2. **Ensure all tests pass**: `pytest tests/ -v`
3. **Lint your code**: `ruff check eden/`
4. **Commit** with clear, descriptive messages:
   - `feat: add WebSocket support`
   - `fix: resolve race condition in rate limiter`
   - `docs: add caching guide`
5. **Push** to your fork and open a **Pull Request**

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Include tests for new functionality
- Update documentation if adding/changing public APIs
- Follow existing code patterns and naming conventions

## Reporting Issues

When filing a bug report, please include:

- Eden version (`eden version`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error traceback (if applicable)

## Code of Conduct

Be respectful, inclusive, and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

---

Thank you for helping make Eden better! 🌱
