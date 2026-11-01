"""Compatibility entry point. Use python -m src.prepare from the repository root."""
from src.prepare import main
from src.common import run_cli

if __name__ == "__main__":
    run_cli(main)
