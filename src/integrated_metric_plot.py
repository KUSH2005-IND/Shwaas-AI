"""Compatibility entry point. Use python -m src.plot from the repository root."""
from src.plot import main
from src.common import run_cli

if __name__ == "__main__":
    run_cli(main)
