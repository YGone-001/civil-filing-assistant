# File: tests/test_ui_responsive_layout.py
# Purpose: Responsive window/layout guarantees (P3B-03 / P3B-13).
# Encoding: UTF-8
"""Layout guarantees for smaller desktops (1366x768 with taskbar/title bar
leaves roughly 1366x700 usable) and large displays.

These are behavioural layout assertions, not pixel snapshots: minimum window
size fits small screens, forms never require horizontal scrolling at the
minimum window size, and the preview dialog never opens larger than the
available screen.
"""

from PySide6.QtWidgets import QApplication, QScrollArea

import pytest

from helpers import make_wizard, prepare_case, select_case, set_parties
from views.pages.export import _PreviewDialog

MIN_WIDTH_BOUND = 1100   # comfortably below the 1366px physical width
MIN_HEIGHT_BOUND = 700   # comfortably below ~700px usable height on 1366x768


def test_minimum_size_fits_small_desktops(qapp):
    wizard, _ = make_wizard()
    minimum = wizard.minimumSize()
    assert 680 <= minimum.width() <= MIN_WIDTH_BOUND, minimum
    assert 560 <= minimum.height() <= MIN_HEIGHT_BOUND, minimum


def test_default_size_respects_available_geometry(qapp):
    """The default geometry is clamped to a fraction of the available screen."""
    wizard, _ = make_wizard()
    screen = wizard.screen() or QApplication.primaryScreen()
    available = screen.availableGeometry()
    size = wizard.size()
    assert size.width() <= max(int(available.width() * 0.92), wizard.minimumSize().width())
    assert size.height() <= max(int(available.height() * 0.9), wizard.minimumSize().height())


@pytest.mark.parametrize("case_type", ["loan", "contract", "property", "labor", "divorce"])
def test_claim_pages_need_no_horizontal_scroll_at_minimum_width(qapp, case_type):
    """At the minimum window size the claim forms must still fit horizontally.

    The page under test must be the wizard's CURRENT page — layout geometry is
    only computed for the visible page."""
    wizard, _ = make_wizard()
    wizard.resize(wizard.minimumSize())
    wizard.show()
    prepare_case(wizard, case_type)
    page_id = {
        "loan": "PAGE_LOAN_CLAIM", "contract": "PAGE_CONTRACT_CLAIM",
        "property": "PAGE_PROPERTY_CLAIM", "labor": "PAGE_LABOR_CLAIM",
        "divorce": "PAGE_DIVORCE_CLAIM",
    }[case_type]
    wizard.setCurrentId(getattr(wizard, page_id))
    qapp.processEvents()
    page = getattr(wizard, {
        "loan": "loan_claim_page", "contract": "contract_claim_page",
        "property": "property_claim_page", "labor": "labor_claim_page",
        "divorce": "divorce_claim_page",
    }[case_type])
    areas = page.findChildren(QScrollArea)
    assert areas, "claim pages wrap their content in a scroll area"
    for area in areas:
        bar = area.horizontalScrollBar()
        assert bar.maximum() == 0, (case_type, bar.maximum())


def test_preview_dialog_never_exceeds_available_screen(qapp):
    wizard, _ = make_wizard()
    prepare_case(wizard, "loan")
    dialog = _PreviewDialog("关键信息预览", "测试预览内容", wizard.export_page)
    screen = dialog.screen() or QApplication.primaryScreen()
    available = screen.availableGeometry()
    size = dialog.size()
    assert size.width() <= available.width(), size
    assert size.height() <= available.height(), size


def test_party_page_needs_no_horizontal_scroll_with_multiple_parties(qapp):
    wizard, _ = make_wizard()
    wizard.resize(wizard.minimumSize())
    wizard.show()
    qapp.processEvents()
    from helpers import select_case, set_parties

    select_case(wizard, "loan")
    set_parties(wizard)
    for _ in range(2):  # two extra parties per side
        wizard.party_page.add_party_ui(0)
        wizard.party_page.add_party_ui(1)
    qapp.processEvents()

    from PySide6.QtWidgets import QScrollArea

    page = wizard.party_page
    for area in page.findChildren(QScrollArea):
        assert area.horizontalScrollBar().maximum() == 0
