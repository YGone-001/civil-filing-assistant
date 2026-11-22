# File: main.py
# Purpose: Application entry point
# Encoding: UTF-8

import argparse
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from views.main_window import LawsuitWizard
from views.theme import apply_theme
from views import dialogs
from presenters.draft_presenter import DraftPresenter
from presenters.main_presenter import MainPresenter
from utils.security_check import SecurityGuard, NetworkStatus


def _resource_path(relative_path):
    """Get absolute path to a bundled resource (dev or PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, relative_path)


def _show_network_notice(status):
    """Show an advisory notice that never overstates the detected state."""
    if status == NetworkStatus.ONLINE:
        # Starting up is safe (nothing entered yet), so continuing is the
        # default and Esc keeps the pre-existing decline-to-continue mapping.
        continue_app = dialogs.confirm(
            None,
            "离线使用建议",
            "检测到本机当前存在网络连接，可能处于联网状态。\n\n"
            "本工具本身不会主动上传案件数据，但在处理真实案件信息时，"
            "建议您在断开网络后使用，以降低数据外泄风险。",
            informative="点击“继续运行”继续启动，或点击“退出程序”结束程序。",
            positive="继续运行",
            negative="退出程序",
            destructive=False,
        )
        if not continue_app:
            sys.exit(0)
    elif status == NetworkStatus.UNKNOWN:
        dialogs.information(
            None,
            "网络状态未知",
            "无法确定本机当前的网络状态（网络检测未成功执行）。\n\n"
            "这并不代表设备已被确认离线。您可以正常继续使用；"
            "如需更高隐私保障，请手动确认网络已断开。",
        )
    # NetworkStatus.OFFLINE: no default route detected, no dialog needed.


def _parse_args(argv):
    """Parse command-line arguments.

    The demo/test-data entry points are hidden by default in production. They
    are only enabled by an explicit ``--demo`` (or ``--dev``) launch argument.
    """
    parser = argparse.ArgumentParser(prog="civil-filing-assistant")
    parser.add_argument(
        "--demo",
        "--dev",
        dest="demo_mode",
        action="store_true",
        help="以演示模式启动，显示测试数据填充入口（仅用于开发与演示）。",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    # Initialize the Qt Application
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    # Set the application window icon (shows in title bar and taskbar).
    icon_path = _resource_path("assets/app_icon.png")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Use Fusion style for a cleaner look on Windows, then apply the app theme.
    app.setStyle("Fusion")
    apply_theme(app)

    # 1. Advisory network-route self-check (not a physical isolation guarantee)
    guard = SecurityGuard()
    status = guard.check_network_status()
    _show_network_notice(status)

    # Create View and Presenter
    wizard = LawsuitWizard(demo_mode=args.demo_mode)
    presenter = MainPresenter(wizard)
    # Explicit, user-initiated draft actions (保存草稿 / 打开草稿). The draft
    # presenter keeps working after it swaps in a restored wizard.
    draft_presenter = DraftPresenter(wizard, presenter)

    # Show the Wizard
    wizard.show()

    # Execute the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()