def main() -> None:
    import sys
    import uvicorn
    from pathlib import Path

    # Ensure the project root (where main.py lives) is importable by uvicorn
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    uvicorn.run("main:app", host="0.0.0.0", port=9999, reload=True)
