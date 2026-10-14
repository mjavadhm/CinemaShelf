"""Ensure no module inside app/ imports from the temporary legacy/ directory."""
from pathlib import Path


def test_app_never_imports_legacy() -> None:
    """Scan all Python files in app/ to guarantee zero dependency on legacy/."""
    app_root = Path(__file__).resolve().parents[2] / "app"
    for py_file in app_root.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert "import legacy" not in content, f"Forbidden legacy import in {py_file}"
        assert "from legacy" not in content, f"Forbidden legacy import in {py_file}"
