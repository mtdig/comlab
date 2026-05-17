def main() -> None:
    import sys
    import uvicorn
    from pathlib import Path

    # Ensure the project root (where main.py lives) is importable by uvicorn
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from app.config import ROOT_PATH
    uvicorn.run("main:app", host="0.0.0.0", port=9999, root_path=ROOT_PATH, reload=True)
