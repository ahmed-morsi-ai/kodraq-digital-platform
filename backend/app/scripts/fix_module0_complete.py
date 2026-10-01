"""Complete Module 0 lesson seed entry point.

Uses the shared, ordering-based specifications and transactional updates from
``fix_module0_lessons`` so all three lesson records stay consistent.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.scripts.fix_module0_lessons import main as update_module0_lessons


def main() -> None:
    update_module0_lessons()


if __name__ == "__main__":
    main()