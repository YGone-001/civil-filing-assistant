# File: views/help_dialog.py
# Purpose: In-app usage guide for the filing wizard.
# Encoding: UTF-8
"""The shared "使用说明" dialog.

The guide is intentionally read-only and uses the same restrained visual
language as the rest of the wizard. It explains the six supported case
categories, the suggested filling order and the points that must be checked
before filing, without turning any of them into a legal conclusion.
"""

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from views.theme import SECONDARY_BUTTON, SPACING_MD

HELP_HTML = """
<style>
    h2 { margin: 0 0 8px 0; }
    h3 { margin: 18px 0 6px 0; }
    p, li { line-height: 1.7; }
    ul, ol { margin-top: 4px; margin-bottom: 8px; }
</style>
<h2>使用说明</h2>
<p>本工具用于辅助整理民事立案材料。请按向导逐步填写，并在生成后逐项核对文书内容。</p>

<h3>一、适用案由与输出</h3>
<ul>
    <li>当前支持六类案由：民间借贷、买卖合同、物业服务合同、劳动报酬／工资追索、离婚析产／抚养费、租赁合同。</li>
    <li>按案件类型和劳动程序阶段生成可编辑 Word 初稿：民事案件为民事起诉状、证据清单、送达地址确认书；劳动争议在申请仲裁前为劳动仲裁申请书、证据清单。</li>
    <li>文书内容由您填写的结构化信息生成；如模板未覆盖您的请求或事实，可在案情页的“补充内容”中填写，补充内容会原样追加。</li>
    <li>最终内容和修改请以导出的 Word 文件为准，并逐项核对。</li>
</ul>

<h3>二、建议填写顺序</h3>
<ol>
    <li>选择案由。</li>
    <li>填写申请人／原告、被申请人／被告及可选的委托代理人。</li>
    <li>填写案情事实、请求和接收机关（法院，或劳动仲裁的仲裁委员会）。</li>
    <li>按提示选择或补充证据。</li>
    <li>核对预览与金额，再生成对应文书。</li>
</ol>

<h3>三、提交前重点核对</h3>
<ul>
    <li>当事人姓名／名称、证件号码、住所地和联系电话是否准确。</li>
    <li>住所地会影响管辖和送达，请按省、市、区、街道、门牌号填写。</li>
    <li>管辖法院或仲裁机构、案由和请求是否与实际情况一致。</li>
    <li>借款本金、利率、欠款期间、物业费、抚养费等金额是否经过人工复核。</li>
    <li>证据名称、证明目的和原件是否齐全；证据清单是否需要补充或删除。</li>
    <li>劳动争议案件请如实选择仲裁程序状态和原告身份。</li>
</ul>

<h3>四、劳动报酬案件的特别提示</h3>
<p>
    劳动争议通常需要先经过劳动仲裁。本工具在“尚未申请劳动仲裁”阶段生成劳动者一方的劳动仲裁申请书与证据清单；
    在其他阶段，只对符合法定起诉条件、且原告为劳动者（员工方）的状态生成起诉状。
    用人单位作为申请人／原告、程序进行中或其他不确定状态会被阻止，并说明原因。
    该限制是本工具员工方模板的产品边界，不否定用人单位依法享有的权利；相关情形请另行准备文书或咨询专业人士。
</p>

<h3>五、免责声明</h3>
<p>
    本工具生成的是辅助整理的可编辑初稿，不构成法律意见，也不能替代律师、仲裁机构或人民法院的专业判断。
    文书中的事实、金额、证据、管辖法院、程序前置条件和当地最新要求，均需由使用者自行核对。
    使用者应对填写内容的真实性、合法性负责；复杂案件、涉及重大权益或特殊情形，请咨询专业律师。
</p>
"""


class HelpDialog(QDialog):
    """A scrollable, read-only usage guide."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用说明")

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MD)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setReadOnly(True)
        self.browser.setAccessibleName("使用说明内容")
        self.browser.setAccessibleDescription("民事立案文书助手的使用说明与免责声明")
        self.browser.document().setDocumentMargin(12)
        self.browser.setHtml(HELP_HTML)
        layout.addWidget(self.browser)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName(SECONDARY_BUTTON)
        close_btn.setAccessibleName("关闭使用说明")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        # Keep the dialog inside the available screen, including on high-DPI or
        # small displays; the content itself scrolls.
        screen = self.screen() or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        if available is not None and available.isValid():
            self.resize(
                min(860, int(available.width() * 0.82)),
                min(680, int(available.height() * 0.82)),
            )
        else:
            self.resize(820, 620)
