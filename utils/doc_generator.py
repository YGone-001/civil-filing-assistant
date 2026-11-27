# File: utils/doc_generator.py
# Purpose: Generate the docx file for lawsuit
# Encoding: UTF-8

import os
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_LINE_SPACING
from docx.oxml.ns import qn

from models.case_model import SERVICE_ADDRESS_SOURCE_LABELS
from models.validation import DateStatus, parse_full_date

class DocumentGenerator:
    def __init__(self):
        self.doc = Document()
        self._set_global_style()

    def reset(self):
        self.doc = Document()
        self._set_global_style()

    def _set_global_style(self):
        # A4 纸 + GB/T 9704-2012 公文版式页边距（上 3.7 / 下 3.5 / 左 2.8 /
        # 右 2.6 cm，版心 15.6×24.7cm）。纸型必须与边距所引用的同一版式配套，
        # 不能停留在 python-docx 的默认 Letter；各类文书共用同一版式设置。
        for section in self.doc.sections:
            section.page_width = Cm(21.0)
            section.page_height = Cm(29.7)
            section.top_margin = Cm(3.7)
            section.bottom_margin = Cm(3.5)
            section.left_margin = Cm(2.8)
            section.right_margin = Cm(2.6)

    def _add_text(self, text, font_name, font_size, bold, align, first_line_indent):
        p = self.doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p.paragraph_format.line_spacing = Pt(28)
        if first_line_indent > 0:
            p.paragraph_format.first_line_indent = Pt(first_line_indent)

        run = p.add_run(text)
        run.bold = bold
        run.font.size = Pt(font_size)
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
        return p

    def add_title(self, text):
        self._add_text(text, "SimSun", 22, True, WD_PARAGRAPH_ALIGNMENT.CENTER, 0)

    def add_heading(self, text):
        p = self._add_text(text, "SimHei", 16, True, WD_PARAGRAPH_ALIGNMENT.LEFT, 0)
        p.paragraph_format.keep_with_next = True

    def add_body(self, text, align=WD_PARAGRAPH_ALIGNMENT.JUSTIFY, first_line_indent=32):
        self._add_text(text, "FangSong_GB2312", 16, False, align, first_line_indent)

    def add_party_block(self, title, parties):
        if len(parties) == 1:
            prefixes = [f"{title}："]
        else:
            prefixes = [f"{title}{i}：" for i in range(1, len(parties) + 1)]

        for i, party in enumerate(parties):
            p = self.doc.add_paragraph()
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
            p.paragraph_format.line_spacing = Pt(28)

            run1 = p.add_run(prefixes[i])
            run1.font.name = "SimHei"
            run1._element.rPr.rFonts.set(qn('w:eastAsia'), "SimHei")
            run1.font.size = Pt(16)
            run1.bold = False

            run2 = p.add_run(self._party_line(party))

            run2.font.name = "FangSong_GB2312"
            run2._element.rPr.rFonts.set(qn('w:eastAsia'), "FangSong_GB2312")
            run2.font.size = Pt(16)

    @staticmethod
    def _birth_text(raw):
        """Format a birth date per the complaint convention, never dropping input.

        A parseable date reads "X年X月X日出生"; anything else falls back to a
        labelled segment with the verbatim text instead of being discarded.
        Blank input contributes no segment at all.
        """
        validation = parse_full_date(raw)
        if validation.status == DateStatus.EMPTY:
            return ""
        if validation.status == DateStatus.VALID and validation.value is not None:
            value = validation.value
            return f"{value.year}年{value.month}月{value.day}日出生"
        return f"出生日期：{raw}"

    @staticmethod
    def _ethnicity_text(raw):
        """Append the 族 suffix once, whatever form the user typed."""
        if not raw or raw.endswith("族"):
            return raw
        return f"{raw}族"

    @classmethod
    def format_party_line(cls, party):
        """Public wrapper used by the on-screen document preview."""
        return cls._party_line(party)

    @staticmethod
    def format_agent_text(agent):
        """Return the agent paragraph text (without the leading label).

        Shared by the DOCX writer and the HTML preview so the two cannot drift
        apart; an absent or nameless agent yields an empty string.
        """
        if agent is None:
            return ""
        name = (getattr(agent, "name", "") or "").strip()
        if not name:
            return ""
        content = name
        agent_type = (getattr(agent, "type", "") or "").strip()
        if agent_type:
            content += f"（{agent_type}）"
        org = (getattr(agent, "org", "") or "").strip()
        if org:
            content += f"，{org}"
        phone = (getattr(agent, "phone", "") or "").strip()
        if phone:
            content += f"，联系电话{phone}"
        return content + "。"

    @classmethod
    def _party_line(cls, party):
        """Join the supplied party details, omitting blank labelled segments.

        Natural-person detail values (gender, birth, ethnicity, occupation)
        read unlabelled — "张三，男，1970年1月1日出生，汉族，务农，住…";
        company parties keep their labelled attribute segments.
        """
        def text(attr):
            return (getattr(party, attr, "") or "").strip()

        if getattr(party, "is_company", False):
            segments = [
                ("统一社会信用代码", text("credit_code")),
                ("法定代表人", text("legal_representative")),
                ("住所地", text("address")),
                ("联系电话", text("phone")),
            ]
            parts = [text("name")] + [f"{label}：{value}" for label, value in segments if value]
        else:
            parts = [part for part in (
                text("name"),
                text("gender"),
                cls._birth_text(text("birth_date")),
                cls._ethnicity_text(text("ethnicity")),
                text("occupation"),
            ) if part]
            segments = [
                ("身份证号", text("id_number")),
                ("住址", text("address")),
                ("联系电话", text("phone")),
            ]
            parts += [f"{label}：{value}" for label, value in segments if value]
        return "，".join(part for part in parts if part) + "。"

    def add_agent_block(self, agent, label="诉讼代理人"):
        """Add the optional agent paragraph after the plaintiff/applicant block."""
        content = self.format_agent_text(agent)
        if not content:
            return

        p = self.doc.add_paragraph()
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p.paragraph_format.line_spacing = Pt(28)

        run1 = p.add_run(f"{label}：")
        run1.font.name = "SimHei"
        run1._element.rPr.rFonts.set(qn('w:eastAsia'), "SimHei")
        run1.font.size = Pt(16)
        run1.bold = False

        run2 = p.add_run(content)
        run2.font.name = "FangSong_GB2312"
        run2._element.rPr.rFonts.set(qn('w:eastAsia'), "FangSong_GB2312")
        run2.font.size = Pt(16)

    def add_claims(self, claims, heading="诉讼请求："):
        self.add_heading(heading)
        for idx, claim in enumerate(claims, 1):
            self.add_body(f"{idx}. {claim}", align=WD_PARAGRAPH_ALIGNMENT.JUSTIFY, first_line_indent=32)

    def add_facts(self, facts_text):
        self.add_heading("事实与理由：")
        # ``all_facts()`` separates the generated narrative and the optional
        # user-supplied note with a blank line; each becomes its own paragraph.
        paragraphs = [part.strip() for part in str(facts_text).split("\n\n") if part.strip()]
        if not paragraphs:
            paragraphs = [""]
        for paragraph in paragraphs:
            self.add_body(
                paragraph,
                align=WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
                first_line_indent=32,
            )

    def add_footer(self, court_name, signer_label="具状人"):
        # Keep "此致", the recipient and the signature block on the same page.
        # A long multi-party complaint must not leave "此致" orphaned at the
        # bottom of one page while the court name starts the next.
        p = self._add_text("此致", "FangSong_GB2312", 16, False, WD_PARAGRAPH_ALIGNMENT.LEFT, 0)
        p.paragraph_format.keep_with_next = True
        p = self._add_text(
            str(court_name or ""), "FangSong_GB2312", 16, False,
            WD_PARAGRAPH_ALIGNMENT.LEFT, 0,
        )
        p.paragraph_format.keep_with_next = True
        p = self._add_text(
            f"{signer_label}：", "FangSong_GB2312", 16, False,
            WD_PARAGRAPH_ALIGNMENT.RIGHT, 0,
        )
        p.paragraph_format.space_before = Pt(28)
        p.paragraph_format.keep_with_next = True
        self._add_text(
            "年   月   日", "FangSong_GB2312", 16, False,
            WD_PARAGRAPH_ALIGNMENT.RIGHT, 0,
        )

    @staticmethod
    def _keep_table_together(table):
        """Prevent a party's address table from splitting across pages."""
        from docx.oxml import OxmlElement

        for row in table.rows:
            tr_pr = row._tr.get_or_add_trPr()
            tr_pr.append(OxmlElement("w:cantSplit"))
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_together = True
                    paragraph.paragraph_format.keep_with_next = True

    @staticmethod
    def _set_table_widths(table, widths):
        """Pin a table to fixed column widths honoured by Word and WPS.

        ``cell.width`` alone only writes ``w:tcW``. WPS keeps the original
        equal ``w:gridCol`` widths in that case, so the evidence header wrapped
        mid-word. The grid, the table width and the fixed layout must all agree.
        """
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        table.autofit = False
        table.allow_autofit = False

        tbl_pr = table._tbl.tblPr
        tbl_w = tbl_pr.find(qn("w:tblW"))
        if tbl_w is None:
            tbl_w = OxmlElement("w:tblW")
            tbl_pr.append(tbl_w)
        tbl_w.set(qn("w:type"), "dxa")
        tbl_w.set(qn("w:w"), str(sum(int(width.twips) for width in widths)))

        for index, width in enumerate(widths):
            column = table.columns[index]
            column.width = width
            for cell in column.cells:
                cell.width = width

    def _set_cell_text(self, cell, text, font_name, font_size, bold, line_spacing=28):
        cell.text = ""
        p = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        p.paragraph_format.line_spacing = Pt(line_spacing)
        run = p.add_run(text)
        run.bold = bold
        run.font.size = Pt(font_size)
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)

    @staticmethod
    def _add_pagination(doc):
        from docx.oxml import OxmlElement

        for section in doc.sections:
            footer = section.footer
            para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

            run = para.add_run("- ")

            fldChar1 = OxmlElement('w:fldChar')
            fldChar1.set(qn('w:fldCharType'), 'begin')

            instrText = OxmlElement('w:instrText')
            instrText.set(qn('xml:space'), 'preserve')
            instrText.text = " PAGE "

            fldChar2 = OxmlElement('w:fldChar')
            fldChar2.set(qn('w:fldCharType'), 'separate')

            fldChar3 = OxmlElement('w:fldChar')
            fldChar3.set(qn('w:fldCharType'), 'end')

            run._r.append(fldChar1)
            run._r.append(instrText)
            run._r.append(fldChar2)
            run._r.append(fldChar3)

            para.add_run(" -")

    def save(self, output_path):
        self.doc.save(output_path)

    def export_complaint(self, model, file_path):
        self.reset()
        self.add_title("民 事 起 诉 状")
        self.doc.add_paragraph()
        self.add_party_block("原告", model.party_manager.plaintiffs)
        self.add_agent_block(getattr(model, "agent", None))
        self.add_party_block("被告", model.party_manager.defendants)
        self.doc.add_paragraph()
        self.add_claims(model.all_claims())
        self.doc.add_paragraph()
        self.add_facts(model.all_facts())
        self.doc.add_paragraph()
        self._add_appendix(model)
        self.add_footer(model.court_name)
        self._add_pagination(self.doc)
        self.save(file_path)

    def export_arbitration_application(self, model, file_path):
        """Write the employee-side labour arbitration application (pre-filing)."""
        self.reset()
        self.add_title("劳 动 仲 裁 申 请 书")
        self.doc.add_paragraph()
        self.add_party_block("申请人", model.party_manager.plaintiffs)
        self.add_agent_block(getattr(model, "agent", None), label="委托代理人")
        self.add_party_block("被申请人", model.party_manager.defendants)
        self.doc.add_paragraph()
        self.add_claims(model.all_arbitration_claims(), heading="仲裁请求：")
        self.doc.add_paragraph()
        self.add_facts(model.all_arbitration_facts())
        self.doc.add_paragraph()
        self._add_appendix(model, copy_label="本申请书")
        self.add_footer(getattr(model, "arb_commission", ""), signer_label="申请人")
        self._add_pagination(self.doc)
        self.save(file_path)

    def _add_appendix(self, model, copy_label="本状"):
        """Add the attachment note: one copy per respondent/defendant.

        The count follows the defendant list actually present in the model, so
        an unusual party setup can never print a wrong number. Users edit the
        exported file to add further attachments.
        """
        defendant_count = len(model.party_manager.defendants)
        if defendant_count <= 0:
            return
        self.add_body(f"附：{copy_label}副本{defendant_count}份。")

    def export_evidence_list(self, model, file_path):
        self.reset()
        self.add_title("证 据 清 单")
        self.doc.add_paragraph()

        table = self.doc.add_table(rows=1, cols=4)
        table.style = "Table Grid"

        hdr = table.rows[0].cells
        self._set_cell_text(hdr[0], "序号", "SimHei", 16, True)
        self._set_cell_text(hdr[1], "证据名称", "SimHei", 16, True)
        self._set_cell_text(hdr[2], "证明对象/目的", "SimHei", 16, True)
        self._set_cell_text(hdr[3], "备注", "SimHei", 16, True)

        for idx, ev in enumerate(getattr(model, "evidences", []) or [], 1):
            row = table.add_row().cells
            self._set_cell_text(row[0], str(idx), "FangSong_GB2312", 16, False)
            self._set_cell_text(row[1], str(ev.name or ""), "FangSong_GB2312", 16, False)
            self._set_cell_text(row[2], str(ev.target or ""), "FangSong_GB2312", 16, False)

            self._set_cell_text(
                row[3], str(getattr(ev, "note", "") or ""), "FangSong_GB2312", 16, False
            )

        # Fixed widths keep the long "证明对象/目的" header on one line and
        # leave the remark column readable without inventing content.
        self._set_table_widths(table, (Cm(1.8), Cm(4.4), Cm(7.2), Cm(2.2)))

        self.save(file_path)

    def export_address_form(self, model, file_path):
        # Address blocks contain six fixed rows per party.  A compact table
        # treatment keeps the common two-party form and its signature together
        # on one page, without changing the readable body-text specification.
        table_font_size = 14
        table_line_spacing = 20
        self.reset()
        self.add_title("送 达 地 址 确 认 书")
        self.doc.add_paragraph()

        self.add_body(
            "为便于人民法院依法送达诉讼文书，当事人现确认以下送达地址信息真实、准确。"
            "下列表格逐一列示向导中已填写的当事人；每一名当事人应分别确认自己的送达地址，"
            "不能以其中一名当事人的地址代表其他当事人。送达地址来源栏区分当事人确认、"
            "他人提供线索和未确认；他人提供线索不等于当事人确认。",
            align=WD_PARAGRAPH_ALIGNMENT.JUSTIFY, first_line_indent=32,
        )
        self.doc.add_paragraph()

        entries = []
        for role, members in (
            ("原告", model.party_manager.plaintiffs),
            ("被告", model.party_manager.defendants),
        ):
            for idx, party in enumerate(members, 1):
                label = role if len(members) == 1 else f"{role}{idx}"
                entries.append((label, party))

        labels = [
            "当事人",
            "姓名/名称",
            "证件号码/统一社会信用代码",
            "联系电话",
            "送达地址",
            "送达地址来源",
            "备注",
        ]

        if not entries:
            entries = [("（未填写当事人）", None)]

        for label, party in entries:
            if party is None:
                name = id_number = phone = addr = ""
                role_text = label
                source_text = SERVICE_ADDRESS_SOURCE_LABELS["unconfirmed"]
            else:
                name = getattr(party, "name", "") or ""
                if getattr(party, "is_company", False):
                    id_number = getattr(party, "credit_code", "") or ""
                else:
                    id_number = getattr(party, "id_number", "") or ""
                phone = getattr(party, "phone", "") or ""
                addr = getattr(party, "address", "") or ""
                role_text = label
                source_text = SERVICE_ADDRESS_SOURCE_LABELS.get(
                    getattr(party, "service_address_source", "unconfirmed"),
                    SERVICE_ADDRESS_SOURCE_LABELS["unconfirmed"],
                )

            table = self.doc.add_table(rows=7, cols=2)
            table.style = "Table Grid"

            values = [
                role_text,
                name,
                id_number,
                phone,
                addr,
                source_text,
                "如地址、电话变更，应及时书面告知人民法院。",
            ]

            for i in range(7):
                self._set_cell_text(
                    table.rows[i].cells[0], labels[i], "SimHei", table_font_size, True,
                    table_line_spacing,
                )
                self._set_cell_text(
                    table.rows[i].cells[1], values[i], "FangSong_GB2312", table_font_size, False,
                    table_line_spacing,
                )

            self._keep_table_together(table)
            confirmation = self._add_text(
                "确认人（本人或有权代收人）：", "FangSong_GB2312", 16, False,
                WD_PARAGRAPH_ALIGNMENT.LEFT, 0,
            )
            confirmation.paragraph_format.keep_with_next = True
            date_line = self._add_text(
                "日期：", "FangSong_GB2312", 16, False,
                WD_PARAGRAPH_ALIGNMENT.LEFT, 0,
            )
            # Small gap after each signature block; the next party's table
            # otherwise starts flush against this date line.
            date_line.paragraph_format.space_after = Pt(12)

        self._add_pagination(self.doc)
        self.save(file_path)
