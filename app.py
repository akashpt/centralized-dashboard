import sys
import os
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

# ===============================
# Platform selection
# ===============================
if IS_LINUX:
    os.environ["QT_QPA_PLATFORM"] = "xcb"
elif IS_WINDOWS:
    os.environ["QT_QPA_PLATFORM"] = "windows"

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel

from classes.bridge import Bridge
from path import INDEX_PAGE, TEMPLATES_DIR, REPORT_PAGE


# ==============================
# MAIN WINDOW
# ==============================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Centralized Dashboard")
        self.resize(1200, 800)

        # -----------------
        # Web View
        # -----------------
        self.view = QWebEngineView()
        self.setCentralWidget(self.view)

        # -----------------
        # Bridge + Channel
        # -----------------
        self.channel = QWebChannel()
        self.bridge = Bridge(self)

      
        self.channel.registerObject("bridge", self.bridge)

        self.view.page().setWebChannel(self.channel)

        # -----------------
        # Load first page
        # -----------------
        index_file = (INDEX_PAGE).resolve()

        print("Loading page:", index_file)

        if index_file.exists():
            self.view.load(QUrl.fromLocalFile(str(index_file)))
        else:
            print("❌ index.html not found:", index_file)

    # =====================================
    # PAGE SWITCH FUNCTION (Bridge uses this)
    # =====================================

    def load_page(self, page_name):

        print(f"Switching to {page_name}")

        file_path = (TEMPLATES_DIR / page_name).resolve()

        if file_path.exists():

            # Clear previous page (important for Linux)
            self.view.setUrl(QUrl("about:blank"))

            # Load new page
            self.view.load(QUrl.fromLocalFile(str(file_path)))

            # Reconnect channel
            self.view.page().setWebChannel(self.channel)

        else:
            print("❌ Page not found:", file_path)

   # =====================================
    # CLOSE EVENT
    # =====================================

    def closeEvent(self, event):

        try:
            self.view.page().runJavaScript(
                "localStorage.removeItem('machineMonitoringSession');"
                "localStorage.removeItem('machineMonitoringUser');"
            )
            if hasattr(self.bridge, "sessionEnded"):
                self.bridge.sessionEnded.emit()
            if hasattr(self.bridge, "stopCamera"):
                self.bridge.stopCamera()
        except Exception as e:
            print("Shutdown cleanup error:", e)

        super().closeEvent(event)


# ==============================
# MAIN ENTRY
# ==============================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
