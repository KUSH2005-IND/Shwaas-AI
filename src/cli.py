"""Convenience entry point; module commands in the README also work."""
import argparse
import importlib
import sys
from src.common import run_cli

def main():
    parser = argparse.ArgumentParser(prog="shwaasai")
    parser.add_argument("command", choices=("prepare", "manifest", "features", "train", "evaluate", "plot"),
                        nargs="?")
    args, remaining = parser.parse_known_args()
    if args.command is None:
        parser.print_help()
        return
    sys.argv = [f"shwaasai {args.command}", *remaining]
    module = importlib.import_module(f"src.{args.command}")
    run_cli(module.main)

if __name__ == "__main__":
    main()
