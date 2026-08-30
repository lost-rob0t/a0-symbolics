import sys
from pathlib import Path

# Make repo-root modules (`helpers`, `plugins`, `extensions`) importable
# regardless of how pytest is invoked or which test directory is targeted.
repo_root = str(Path(__file__).resolve().parent)
while repo_root in sys.path:
    sys.path.remove(repo_root)
sys.path.insert(0, repo_root)
