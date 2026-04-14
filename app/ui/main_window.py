from datetime import datetime
from pathlib import Path
from typing import List
import re, shutil

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)
from app.core.models.ui import UIState
from app.ui.generation_controller import GenerationController
from app.ui.styles import (
    get_global_stylesheet,
    ACCENT, ACCENT_HOVER, ACCENT_LIGHT, ACCENT_SOFT,
    BG_BASE, BG_SURFACE, BG_SIDEBAR, BG_PILL_HOVER, BG_PILL_SEL,
    BORDER, BORDER_LIGHT, BORDER_FOCUS,
    DOT_DONE, DOT_CURRENT, DOT_PENDING, DOT_LINE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_ON_ACCENT,
    R_SM, R_MD, R_LG, SIDEBAR_W,
)
from app.ui.chat_widget import ChatQuestionnaireWidget, ProgressBarWidget

STEPS = ["配置", "模板选择", "需求问答", "生成文档", "查看结果"]
S_CFG = 0; S_TPL = 1; S_QA = 2; S_GEN = 3; S_PRE = 4


# ── 通用构建工具 ──

def _mk_title(t):
    l = QLabel(t)
    l.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {TEXT_PRIMARY};")
    return l

def _mk_desc(t):
    l = QLabel(t); l.setWordWrap(True)
    l.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
    return l

def _mk_card():
    f = QFrame(); f.setObjectName("crd")
    f.setStyleSheet(
        f"QFrame#crd {{ background: {BG_SURFACE}; border: 1px solid {BORDER}; border-radius: {R_LG}; }}"
    )
    return f

def _mk_accent_btn(t):
    b = QPushButton(t); b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton {{ background: {ACCENT}; color: {TEXT_ON_ACCENT}; border: none;"
        f"  border-radius: {R_MD}; padding: 9px 22px; font-weight: 600; font-size: 14px; }}"
        f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
    )
    return b

def _mk_field(layout, label, placeholder, echo=False):
    lb = QLabel(label)
    lb.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY}; background: transparent;")
    inp = QLineEdit(); inp.setPlaceholderText(placeholder)
    if echo: inp.setEchoMode(QLineEdit.Password)
    layout.addWidget(lb); layout.addWidget(inp)
    return inp

def _mk_nav(prev="← 上一步", nxt="下一步 →"):
    bar = QFrame(); bar.setFixedHeight(56)
    bar.setStyleSheet(f"QFrame {{ background: {BG_SURFACE}; border-top: 1px solid {BORDER_LIGHT}; }}")
    lay = QHBoxLayout(bar); lay.setContentsMargins(28, 0, 28, 0)
    pb = QPushButton(prev); pb.setCursor(Qt.PointingHandCursor)
    pb.setStyleSheet(
        f"QPushButton {{ background: transparent; border: 1px solid {BORDER};"
        f"  border-radius: {R_MD}; padding: 8px 20px; color: {TEXT_SECONDARY}; font-size: 14px; }}"
        f"QPushButton:hover {{ background: {BG_PILL_HOVER}; color: {TEXT_PRIMARY}; }}"
    )
    nb = QPushButton(nxt); nb.setCursor(Qt.PointingHandCursor)
    nb.setStyleSheet(
        f"QPushButton {{ background: {ACCENT}; border: none; border-radius: {R_MD};"
        f"  padding: 8px 24px; color: {TEXT_ON_ACCENT}; font-weight: 600; font-size: 14px; }}"
        f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
    )
    lay.addWidget(pb); lay.addStretch(1); lay.addWidget(nb)
    return bar, pb, nb


# ── 后台线程 ──

class GenerationWorker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, ctrl, req, name):
        super().__init__()
        self.ctrl = ctrl; self.req = req; self.name = name
    def run(self):
        self.finished.emit(self.ctrl.run_with_requirement(self.req, output_name=self.name))


# ══════════════════════════════════════
#  侧边栏
# ══════════════════════════════════════

class StepDot(QWidget):
    DONE = "done"; CURRENT = "current"; PENDING = "pending"

    def __init__(self, text, is_first=False, is_last=False, parent=None):
        super().__init__(parent)
        self.label = text; self.status = self.PENDING
        self.is_first = is_first; self.is_last = is_last
        self.setFixedHeight(36); self.setMinimumWidth(150)

    def set_status(self, s):
        self.status = s; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        colors = {self.DONE: QColor(DOT_DONE), self.CURRENT: QColor(DOT_CURRENT), self.PENDING: QColor(DOT_PENDING)}
        c = colors[self.status]
        cx, cy, r = 10, self.height() // 2, 5

        # 连接线
        p.setPen(QPen(QColor(DOT_LINE), 1.2))
        if not self.is_first: p.drawLine(cx, 0, cx, cy - r - 1)
        if not self.is_last:  p.drawLine(cx, cy + r + 1, cx, self.height())

        # 圆点
        if self.status == self.PENDING:
            p.setPen(QPen(c, 1.5)); p.setBrush(Qt.NoBrush)
        else:
            p.setPen(Qt.NoPen); p.setBrush(c)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # 文字
        tc = colors[self.status] if self.status == self.CURRENT else (
            QColor(TEXT_PRIMARY) if self.status == self.DONE else QColor(TEXT_TERTIARY))
        p.setPen(tc)
        f = p.font(); f.setFamily("Microsoft YaHei"); f.setPixelSize(15)
        f.setBold(self.status == self.CURRENT); p.setFont(f)
        p.drawText(26, 0, self.width() - 26, self.height(), Qt.AlignVCenter | Qt.AlignLeft, self.label)
        p.end()


class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar"); self.setFixedWidth(SIDEBAR_W)
        self.dots: List[StepDot] = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 24, 12, 16); lay.setSpacing(0)

        brand = QLabel("师 爷")
        brand.setStyleSheet(
            f"font-size: 28px; font-weight: 800; color: {TEXT_PRIMARY};"
            "background: transparent; letter-spacing: 4px;"
        )
        lay.addWidget(brand)

        sub = QLabel("AI写内容  LaTeX管排版")
        sub.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; background: transparent; margin-top: 4px;")
        lay.addWidget(sub)
        lay.addSpacing(28)

        for i, label in enumerate(STEPS):
            d = StepDot(label, is_first=(i == 0), is_last=(i == len(STEPS) - 1))
            lay.addWidget(d); self.dots.append(d)

        lay.addSpacing(24)
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background: {BORDER};")
        lay.addWidget(sep); lay.addSpacing(14)

        hl = QLabel("最近生成")
        hl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY}; background: transparent;")
        lay.addWidget(hl); lay.addSpacing(8)
        self.history_list = QListWidget()
        lay.addWidget(self.history_list, 1)

    def set_step(self, active, completed):
        for i, d in enumerate(self.dots):
            if i == active:     d.set_status(StepDot.CURRENT)
            elif i < completed: d.set_status(StepDot.DONE)
            else:               d.set_status(StepDot.PENDING)

    def append_history(self, text, payload):
        it = QListWidgetItem(text); it.setData(Qt.UserRole, payload)
        self.history_list.insertItem(0, it)


# ══════════════════════════════════════
#  Page 0 — API 配置
# ══════════════════════════════════════

class ConfigPage(QWidget):
    saved = pyqtSignal()
    go_next = pyqtSignal()

    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 32, 40, 0)
        outer.setSpacing(10)

        # 标题在顶部
        outer.addWidget(_mk_title("API 配置"))
        outer.addWidget(_mk_desc("配置大模型 API 连接信息。已有配置可直接点击「下一步」。"))

        # 卡片居中
        outer.addStretch(1)
        card = _mk_card()

        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24); cl.setSpacing(12)
        self.api_key  = _mk_field(cl, "API Key", "输入你的 API Key", True)
        self.base_url = _mk_field(cl, "Base URL", "https://api.deepseek.com")
        self.model    = _mk_field(cl, "模型名称", "deepseek-chat")
        cl.addSpacing(4)
        r = QHBoxLayout(); r.addStretch(1)
        sb = _mk_accent_btn("保存配置"); sb.clicked.connect(self._save)
        r.addWidget(sb); cl.addLayout(r)
        outer.addWidget(card)
        outer.addStretch(2)

        # 底栏
        footer, _, nxt = _mk_nav()
        _.setVisible(False)
        nxt.clicked.connect(self.go_next.emit)
        outer.addWidget(footer)

    def load(self):
        cfg = self.project_root / "call_example.py"
        if cfg.exists():
            c = cfg.read_text(encoding="utf-8")
            m = re.search(r'api_key="([^"]*)"', c)
            if m: self.api_key.setText(m.group(1))
            m = re.search(r'base_url="([^"]*)"', c)
            if m: self.base_url.setText(m.group(1))
        mf = self.project_root / "model_config.txt"
        self.model.setText(mf.read_text(encoding="utf-8").strip() if mf.exists() else "deepseek-chat")

    def has_config(self):
        return bool(self.api_key.text().strip())

    def _save(self):
        ak = self.api_key.text().strip()
        bu = self.base_url.text().strip() or "https://api.deepseek.com"
        mo = self.model.text().strip() or "deepseek-chat"
        if not ak:
            QMessageBox.warning(self, "提示", "请输入 API Key"); return

        cfg = self.project_root / "call_example.py"
        ct = cfg.read_text(encoding="utf-8") if cfg.exists() else (
            'from openai import OpenAI\n\nclient = OpenAI(\n'
            '    api_key="",\n    base_url="https://api.deepseek.com",\n)\n')
        ct = re.sub(r'api_key="[^"]*"', f'api_key="{ak}"', ct) if 'api_key="' in ct else ct + f'\napi_key="{ak}"\n'
        ct = re.sub(r'base_url="[^"]*"', f'base_url="{bu}"', ct) if 'base_url="' in ct else ct + f'\nbase_url="{bu}"\n'
        cfg.write_text(ct, encoding="utf-8")
        (self.project_root / "model_config.txt").write_text(mo, encoding="utf-8")
        QMessageBox.information(self, "成功",
            f"已保存，重启生效。\nAPI Key: {ak[:10]}…\nBase URL: {bu}\n模型: {mo}")
        self.saved.emit()


# ══════════════════════════════════════
#  Page 1 — 模板选择
# ══════════════════════════════════════

class TemplatePage(QWidget):
    go_prev = pyqtSignal()
    go_next = pyqtSignal()
    template_chosen = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent); self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 32, 40, 0)
        outer.setSpacing(10)

        outer.addWidget(_mk_title("选择模板"))
        outer.addWidget(_mk_desc("选择一个 LaTeX 排版模板。如无特殊需求可直接下一步。"))
        outer.addSpacing(6)

        card = _mk_card()
        cl = QVBoxLayout(card); cl.setContentsMargins(24, 24, 24, 24); cl.setSpacing(12)
        lb = QLabel("模板")
        lb.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY}; background: transparent;")
        cl.addWidget(lb)
        self.combo = QComboBox(); cl.addWidget(self.combo)
        outer.addWidget(card)

        outer.addStretch(1)

        footer, pb, nb = _mk_nav()
        pb.clicked.connect(self.go_prev.emit)
        nb.clicked.connect(self._confirm)
        outer.addWidget(footer)

    def load_templates(self, names):
        self.combo.clear(); self.combo.addItems(names)

    def current_template(self):
        return self.combo.currentText() or "default"

    def _confirm(self):
        self.template_chosen.emit(self.current_template())
        self.go_next.emit()


# ══════════════════════════════════════
#  Page 2 — 需求问答
# ══════════════════════════════════════

class QuestionnairePage(QWidget):
    go_prev = pyqtSignal()
    generate_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._qa_started = False
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # 可滚动内容
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent;")
        inner = QWidget(); inner.setStyleSheet("background: transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(40, 28, 40, 12); il.setSpacing(10)

        il.addWidget(_mk_title("需求采集"))
        il.addWidget(_mk_desc("回答以下问题以生成精准文档。点击选项即可，随时可修改。"))
        il.addSpacing(4)

        self.chat = ChatQuestionnaireWidget()
        self.chat.setStyleSheet("background: transparent;")
        il.addWidget(self.chat, 1)

        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # 底栏
        bottom = QFrame()
        bottom.setStyleSheet(f"QFrame {{ background: {BG_SURFACE}; border-top: 1px solid {BORDER_LIGHT}; }}")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(28, 10, 28, 12); bl.setSpacing(8)

        pr = QHBoxLayout(); pr.setSpacing(10)
        self.prog_bar = ProgressBarWidget(); pr.addWidget(self.prog_bar, 1)
        self.prog_label = QLabel("0/0")
        self.prog_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; min-width: 32px;")
        self.prog_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pr.addWidget(self.prog_label); bl.addLayout(pr)

        br = QHBoxLayout(); br.setSpacing(8)
        self.prev_btn = QPushButton("← 上一步"); self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {BORDER};"
            f"  border-radius: {R_MD}; padding: 8px 20px; color: {TEXT_SECONDARY}; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {BG_PILL_HOVER}; color: {TEXT_PRIMARY}; }}"
        )
        self.prev_btn.clicked.connect(self.go_prev.emit)
        br.addWidget(self.prev_btn); br.addStretch(1)

        self.gen_btn = QPushButton("生成文档"); self.gen_btn.setCursor(Qt.PointingHandCursor)
        self.gen_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: {TEXT_ON_ACCENT}; border: none;"
            f"  border-radius: {R_MD}; padding: 9px 28px; font-weight: 600; font-size: 14px; min-width: 140px; }}"
            f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
            f"QPushButton:disabled {{ background: {BORDER}; color: {TEXT_TERTIARY}; }}"
        )
        self.gen_btn.setEnabled(False)
        self.gen_btn.clicked.connect(self.generate_clicked.emit)
        br.addWidget(self.gen_btn); bl.addLayout(br)
        root.addWidget(bottom)

        self.chat.progress_changed.connect(self._prog)
        self.chat.questionnaire_completed.connect(self._done)

    def start(self, fields, req, ctrl):
        self._qa_started = True
        self.chat.start_session(fields, req, ctrl)
        self.gen_btn.setEnabled(False)

    @property
    def qa_started(self):
        return self._qa_started

    def _prog(self, done, shown, total):
        self.prog_bar.set_progress(done, shown, total)
        self.prog_label.setText(f"{done}/{total}")

    def _done(self, _):
        self.gen_btn.setEnabled(True)


# ══════════════════════════════════════
#  Page 3 — 生成中
# ══════════════════════════════════════

class GeneratingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setAlignment(Qt.AlignCenter)
        l = QLabel("正在生成文档…"); l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {TEXT_SECONDARY};")
        lay.addWidget(l)
        s = QLabel("AI 正在撰写内容并编译 LaTeX，请稍候"); s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet(f"font-size: 12px; color: {TEXT_TERTIARY};")
        lay.addWidget(s)


# ══════════════════════════════════════
#  Page 4 — 查看结果
# ══════════════════════════════════════

class PreviewPage(QWidget):
    go_prev = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_path = ""; self.page_idx = 0; self.page_cnt = 0; self.zoom = 1.3
        self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)

        # 左侧预览
        left = QVBoxLayout(); left.setContentsMargins(28, 24, 16, 0); left.setSpacing(12)
        left.addWidget(_mk_title("查看结果"))

        tb = QHBoxLayout(); tb.setSpacing(8)
        self.btn_pp = self._ib("◀"); self.btn_pp.clicked.connect(self._pp); tb.addWidget(self.btn_pp)
        self.lbl_pg = QLabel("0/0"); self.lbl_pg.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; padding: 0 4px;"); tb.addWidget(self.lbl_pg)
        self.btn_np = self._ib("▶"); self.btn_np.clicked.connect(self._np); tb.addWidget(self.btn_np)
        tb.addSpacing(10)
        self.btn_zo = self._ib("−"); self.btn_zo.clicked.connect(self._zo); tb.addWidget(self.btn_zo)
        self.lbl_zm = QLabel("130%"); self.lbl_zm.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY}; padding: 0 3px;"); tb.addWidget(self.lbl_zm)
        self.btn_zi = self._ib("+"); self.btn_zi.clicked.connect(self._zi); tb.addWidget(self.btn_zi)
        tb.addStretch(1)
        self.btn_dl = QPushButton("下载 PDF"); self.btn_dl.setCursor(Qt.PointingHandCursor)
        self.btn_dl.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: {TEXT_ON_ACCENT}; border: none;"
            f"  border-radius: {R_MD}; padding: 7px 16px; font-weight: 600; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
            f"QPushButton:disabled {{ background: {BORDER}; color: {TEXT_TERTIARY}; }}"
        )
        self.btn_dl.setEnabled(False); self.btn_dl.clicked.connect(self._dl); tb.addWidget(self.btn_dl)
        left.addLayout(tb)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet(f"QScrollArea {{ background: {BG_BASE}; border: 1px solid {BORDER}; border-radius: {R_LG}; }}")
        cont = QWidget(); cont.setStyleSheet("background: transparent;")
        cll = QVBoxLayout(cont); cll.setContentsMargins(20, 16, 20, 16)
        self.lbl_preview = QLabel("生成完成后 PDF 预览将显示在此处")
        self.lbl_preview.setAlignment(Qt.AlignCenter); self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setMinimumSize(300, 300)
        self.lbl_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_preview.setStyleSheet(f"color: {TEXT_TERTIARY}; font-size: 15px; background: transparent;")
        cll.addWidget(self.lbl_preview, 0, Qt.AlignHCenter | Qt.AlignVCenter); cll.addStretch(1)
        self.scroll.setWidget(cont); left.addWidget(self.scroll, 1)
        lw = QWidget(); lw.setLayout(left); body.addWidget(lw, 1)

        # 右侧摘要
        right = QFrame(); right.setFixedWidth(260)
        right.setStyleSheet(f"QFrame {{ background: {BG_SURFACE}; border-left: 1px solid {BORDER_LIGHT}; }}")
        rl = QVBoxLayout(right); rl.setContentsMargins(16, 24, 16, 16); rl.setSpacing(12)
        rl.addWidget(self._sl("结果摘要"))
        self.summary = QTextEdit(); self.summary.setReadOnly(True); self.summary.setPlaceholderText("生成信息")
        rl.addWidget(self.summary, 1)
        rl.addWidget(self._sl("运行日志"))
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setPlaceholderText("编译日志")
        self.log.setStyleSheet(f"QTextEdit {{ font-family: 'Consolas', monospace; font-size: 11px; }}")
        rl.addWidget(self.log, 1)
        body.addWidget(right)

        bw = QWidget(); bw.setLayout(body); root.addWidget(bw, 1)
        footer, pb, nb = _mk_nav("← 返回问答", "")
        nb.setVisible(False); pb.clicked.connect(self.go_prev.emit)
        root.addWidget(footer)
        self._uc()

    def _ib(self, c):
        b = QPushButton(c); b.setFixedSize(28, 28); b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {BORDER};"
            f"  border-radius: {R_SM}; font-size: 14px; color: {TEXT_SECONDARY}; }}"
            f"QPushButton:hover {{ background: {BG_PILL_HOVER}; }}"
            f"QPushButton:disabled {{ color: {BORDER}; border-color: {BORDER_LIGHT}; }}"
        )
        b.setEnabled(False); return b

    @staticmethod
    def _sl(t):
        l = QLabel(t)
        l.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY}; background: transparent;")
        return l

    def set_pdf(self, p):
        self.pdf_path = p; self.page_idx = 0; self.page_cnt = self._cnt(p)
        self._render(p, 0); self._uc()

    def _cnt(self, p):
        if not p or not Path(p).exists(): return 0
        try:
            import fitz; d = fitz.open(p); c = int(d.page_count); d.close(); return c
        except Exception: return 0

    def _render(self, p, i=0):
        if not p or not Path(p).exists():
            self.lbl_preview.setText("生成完成后 PDF 预览将显示在此处")
            self.lbl_preview.setPixmap(QPixmap()); return
        try: import fitz
        except Exception: self.lbl_preview.setText("未安装 PyMuPDF"); return
        try:
            d = fitz.open(p)
            if i < 0 or i >= d.page_count: i = 0
            pg = d.load_page(i)
            mat = fitz.Matrix(self.zoom, self.zoom)
            px = pg.get_pixmap(matrix=mat, alpha=False)
            img = QImage(px.samples, px.width, px.height, px.stride, QImage.Format_RGB888)
            self.lbl_preview.setPixmap(QPixmap.fromImage(img.copy()))
            self.lbl_preview.setText(""); self.lbl_preview.adjustSize()
            self.page_cnt = int(d.page_count); self.page_idx = i; d.close(); self._uc()
        except Exception as e:
            self.lbl_preview.setText(f"预览失败: {e}")

    def _uc(self):
        h = self.page_cnt > 0
        self.btn_pp.setEnabled(h and self.page_idx > 0)
        self.btn_np.setEnabled(h and self.page_idx < self.page_cnt - 1)
        self.btn_dl.setEnabled(h); self.btn_zi.setEnabled(h); self.btn_zo.setEnabled(h)
        self.lbl_pg.setText(f"{self.page_idx + 1}/{self.page_cnt}" if h else "0/0")
        self.lbl_zm.setText(f"{int(self.zoom * 100)}%")

    def _pp(self):
        if self.page_idx > 0: self.page_idx -= 1; self._render(self.pdf_path, self.page_idx)
    def _np(self):
        if self.page_idx < self.page_cnt - 1: self.page_idx += 1; self._render(self.pdf_path, self.page_idx)
    def _zi(self):
        self.zoom = min(self.zoom + 0.2, 3.0); self._render(self.pdf_path, self.page_idx)
    def _zo(self):
        self.zoom = max(self.zoom - 0.2, 0.5); self._render(self.pdf_path, self.page_idx)
    def _dl(self):
        if not self.pdf_path or not Path(self.pdf_path).exists():
            QMessageBox.warning(self, "提示", "没有可导出的 PDF"); return
        sp, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF", f"师爷导出_{datetime.now().strftime('%H%M%S')}.pdf", "PDF (*.pdf)")
        if sp:
            try: shutil.copy(self.pdf_path, sp); QMessageBox.information(self, "成功", f"已保存至：\n{sp}")
            except Exception as e: QMessageBox.critical(self, "错误", f"保存失败：{e}")


# ══════════════════════════════════════
#  主窗口
# ══════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.controller = GenerationController(project_root=project_root)
        self.state = UIState()
        self.worker = None
        self._step = 0; self._completed = 0; self._sel_tpl = ""

        self.setWindowTitle("师爷 LaTeX 排版工具")
        self.resize(1280, 820); self.setMinimumSize(960, 640)
        self._build()
        self.setStyleSheet(get_global_stylesheet())
        self.config_page.load()
        self._load_tpl()

        if self.config_page.has_config():
            self._completed = 1; self._go(S_TPL)
        else:
            self._go(S_CFG)

    def _build(self):
        central = QWidget(); central.setObjectName("centralRoot")
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.history_list.itemClicked.connect(self._on_hist)
        root.addWidget(self.sidebar)

        self.stack = QStackedWidget()

        self.config_page = ConfigPage(self.project_root)
        self.config_page.saved.connect(lambda: self._mark(1))
        self.config_page.go_next.connect(lambda: self._advance(S_TPL))

        self.tpl_page = TemplatePage()
        self.tpl_page.go_prev.connect(lambda: self._go(S_CFG))
        self.tpl_page.go_next.connect(self._go_qa)
        self.tpl_page.template_chosen.connect(lambda n: setattr(self, '_sel_tpl', n))

        self.qa_page = QuestionnairePage()
        self.qa_page.go_prev.connect(lambda: self._go(S_TPL))
        self.qa_page.generate_clicked.connect(self._do_gen)

        self.gen_page = GeneratingPage()

        self.preview_page = PreviewPage()
        self.preview_page.go_prev.connect(lambda: self._go(S_QA))

        for p in [self.config_page, self.tpl_page, self.qa_page, self.gen_page, self.preview_page]:
            self.stack.addWidget(p)

        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    def _go(self, s):
        self._step = s; self.stack.setCurrentIndex(s)
        self.sidebar.set_step(s, self._completed)

    def _advance(self, s):
        self._completed = max(self._completed, s); self._go(s)

    def _mark(self, n):
        self._completed = max(self._completed, n)
        self.sidebar.set_step(self._step, self._completed)

    def _go_qa(self):
        self._sel_tpl = self.tpl_page.current_template()
        self._completed = max(self._completed, 2)
        if not self.qa_page.qa_started:
            req = self.controller.questionnaire.get_question_fields()
            af = list(req)
            for f in ["has_images", "has_tables", "references_required"]:
                if f not in af and self.controller.questionnaire.get_question(f):
                    af.append(f)
            self.qa_page.start(af, list(req), self.controller)
        self._go(S_QA)

    def _load_tpl(self):
        self.tpl_page.load_templates(self.controller.available_templates() or ["default"])

    def _do_gen(self):
        if self.state.busy: return
        if not self.qa_page.chat.is_complete:
            QMessageBox.information(self, "提示", "请先完成所有问答。"); return

        r = dict(self.qa_page.chat.get_answers())
        r["template_id"] = self._sel_tpl or "default"
        r.setdefault("has_images", False)
        r.setdefault("has_tables", False)
        r.setdefault("references_required", False)

        self.state.busy = True
        self.qa_page.gen_btn.setEnabled(False)
        self._completed = max(self._completed, 3)
        self._go(S_GEN)

        self.worker = GenerationWorker(self.controller, r, "ui_run")
        self.worker.finished.connect(self._on_result)
        self.worker.start()

    def _on_result(self, result):
        self.state.busy = False
        self.qa_page.gen_btn.setEnabled(True)
        self.state.last_message = result.message
        self.state.last_pdf_path = result.pdf_path
        self.state.last_tex_path = result.tex_path
        self._completed = max(self._completed, 5)
        self._go(S_PRE)

        if result.success:
            self.preview_page.set_pdf(result.pdf_path)
            self.preview_page.summary.setPlainText(
                f"模板：{self._sel_tpl}\nPDF：{result.pdf_path}\n"
                f"TeX：{result.tex_path}\n"
                f"Outline：{' / '.join(result.outline) if result.outline else '-'}")
            if result.logs:
                self.preview_page.log.setPlainText("\n".join(result.logs))
            ts = datetime.now().strftime("%H:%M")
            self.sidebar.append_history(
                f"{self._sel_tpl}\n{ts} · 成功",
                {"pdf_path": result.pdf_path, "tex_path": result.tex_path, "message": result.message})
        else:
            self.preview_page.summary.setPlainText(result.message)
            if result.logs:
                self.preview_page.log.setPlainText("\n".join(result.logs))
            QMessageBox.warning(self, "生成失败", result.message)

    def _on_hist(self, item):
        p = item.data(Qt.UserRole) or {}
        pdf = p.get("pdf_path", "")
        if pdf:
            self._go(S_PRE)
            self.preview_page.set_pdf(pdf)
            self.preview_page.summary.setPlainText(
                f"{p.get('message', '')}\nPDF：{pdf}\nTeX：{p.get('tex_path', '')}")