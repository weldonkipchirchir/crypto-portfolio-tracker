"""Stable repository paths, independent of the current working directory."""
import json
from functools import lru_cache
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[2]
@lru_cache(maxsize=1)
def source_paths():
 return json.loads((PROJECT_ROOT/'config/source_paths.json').read_text(encoding='utf-8'))
def source_path(name):
 path=Path(name)
 if path.is_absolute():return path
 return PROJECT_ROOT/source_paths().get(path.as_posix(),path.as_posix())
