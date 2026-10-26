"""Local syntax validation only (does not require GPU or Docker)."""
from pathlib import Path
import ast
import zipfile
base=Path(__file__).resolve().parents[1]
for p in [base/'smoke/server.py',base/'prototype_kandinsky/service/api.py']:
    ast.parse(p.read_text(encoding='utf-8'))
for name in ['smoke/Dockerfile','.github/workflows/publish.yml','prototype_kandinsky/Dockerfile','README_GR.md']:
    assert (base/name).is_file(),name
try:
    import yaml
    wf=yaml.safe_load((base/'.github/workflows/publish.yml').read_text(encoding='utf-8'))
    assert isinstance(wf,dict)
except ImportError:
    pass
print('PASS: files and Python syntax checked. Docker/GPU NOT tested.')
