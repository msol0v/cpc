import sys
from PyQt5 import QtWidgets
from main_window import MainWindow
import os
import psutil

process = psutil.Process(os.getpid())
if os.name == 'nt':
    process.nice(psutil.HIGH_PRIORITY_CLASS)

def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
