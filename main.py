# File: main.py
# Purpose: Application entry point
# Encoding: UTF-8

import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from views.main_window import LawsuitWizard
from presenters.main_presenter import MainPresenter
from utils.security_check import SecurityGuard

def main():
    # Initialize the Qt Application
    app = QApplication(sys.argv)

    # Use Fusion style for a cleaner look on Windows
    app.setStyle("Fusion")

    # 1. Environment Self-Check (Air-Gapped Validation)
    guard = SecurityGuard()
    if not guard.check_network_status():
        # Network might be active, warn the user
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("物理隔离安全提示")
        msg.setText("检测到您的计算机当前可能连接着网络！\n\n为了达到最高级别的隐私保护（防窃取、防上传），强烈建议您在断开网络（拔掉网线或关闭 Wi-Fi）后使用本软件。")
        msg.setInformativeText("点击“Yes”以隐私模式继续运行，或点击“No”退出程序。")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        ret = msg.exec()
        if ret == QMessageBox.No:
            sys.exit(0)

    # Create View and Presenter
    wizard = LawsuitWizard()
    presenter = MainPresenter(wizard)

    # Show the Wizard
    wizard.show()

    # Execute the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
