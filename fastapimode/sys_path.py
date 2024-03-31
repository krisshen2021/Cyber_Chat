import sys
from pathlib import Path
project_root = str(Path(__file__).parents[1])
def create_syspath():
    if project_root not in sys.path:
        sys.path.append(project_root)
