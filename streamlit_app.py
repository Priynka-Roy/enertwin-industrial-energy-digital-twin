"""Portable Streamlit Community Cloud entry point."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from app.main import main  # noqa: E402

main()
