"""Train the mel-summary/logistic-regression baseline on frozen splits."""
import sys
from src.common import run_cli
from src.train import main

if __name__ == "__main__":
    if "--encoder" in sys.argv:
        raise SystemExit("Use python -m src.train for other encoders.")
    sys.argv.extend(["--encoder", "mel"])
    run_cli(main)
