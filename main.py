# File: main.py
# Purpose: Application entry point
# Encoding: UTF-8

import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from views.main_window import LawsuitWizard
from presenters.main_presenter import MainPresenter
from utils.security_check import SecurityGuard, NetworkStatus


def _show_network_notice(status):
    """Show an advisory notice that never overstates the detected state."""
    msg = QMessageBox()
    if status == NetworkStatus.ONLINE:
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("离线使用建议")
        msg.setText(
            "检测到本机当前存在默认网络路由，可能处于联网状态。\n\n"
            "本工具本身不会主动上传案件数据，但在处理真实案件信息时，"
            "建议您在断开网络后使用，以降低数据外泄风险。"
        )
        msg.setInformativeText("点击“Yes”继续运行，或点击“No”退出程序。")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        if msg.exec() == QMessageBox.No:
            sys.exit(0)
    elif status == NetworkStatus.UNKNOWN:
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("网络状态未知")
        msg.setText(
            "无法确定本机当前的网络状态（路由检测未成功执行）。\n\n"
            "这并不代表设备已被确认离线。您可以正常继续使用；"
            "如需更高隐私保障，请手动确认网络已断开。"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
    # NetworkStatus.OFFLINE: no default route detected, no dialog needed.


def main():
    # Initialize the Qt Application
    app = QApplication(sys.argv)

    # Use Fusion style for a cleaner look on Windows
    app.setStyle("Fusion")

    # 1. Advisory network-route self-check (not a physical isolation guarantee)
    guard = SecurityGuard()
    status = guard.check_network_status()
    _show_network_notice(status)

    # Create View and Presenter
    wizard = LawsuitWizard()
    presenter = MainPresenter(wizard)

    # Show the Wizard
    wizard.show()

    # Execute the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
