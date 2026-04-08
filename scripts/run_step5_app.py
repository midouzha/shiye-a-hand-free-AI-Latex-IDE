import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(PROJECT_ROOT)
    window.show()
    window.raise_()
    window.activateWindow()
    window.showMaximized()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
