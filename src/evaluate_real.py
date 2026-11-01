"""Compatibility entry point. Use python -m src.evaluate from the repository root."""
from src.evaluate import main
from src.common import run_cli

if __name__ == "__main__":
    run_cli(main)
