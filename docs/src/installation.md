# Installation

TSM can be installed using several methods. Choose the one that best fits your needs.

## Prerequisites

Before installing TSM, ensure you have:

- Docker installed and running
- Python 3.8 or higher (for pip installation)
- Basic understanding of Docker and Traefik concepts

## Installation Methods

### Using Homebrew (macOS/Linux)

```bash
brew install auser/tap/tsm
```

### Using the Install Script

```bash
curl -LsSf https://raw.githubusercontent.com/auser/tsm/main/install.sh | sh
```

### Using pip

```bash
pip install tsm
```

## Post-Installation

After installation, you should:

1. Install dependencies:
   ```bash
   tsm install-deps
   ```

2. Verify the installation:
   ```bash
   tsm version
   ```

## Next Steps

Once TSM is installed, proceed to the [Quickstart](./quickstart.md) guide to begin using TSM.
