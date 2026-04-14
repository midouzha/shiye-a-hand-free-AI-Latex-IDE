#问答组件
 
from typing import Any, Dict, List, Optional
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from app.ui.styles import (
    ACCENT, ACCENT_HOVER, ACCENT_SOFT,
    BG_QUESTION, BG_PILL, BG_PILL_HOVER, BG_PILL_SEL, BG_SURFACE,
    BORDER, BORDER_FOCUS,
    PROGRESS_DONE, PROGRESS_CUR, PROGRESS_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_ON_ACCENT,
    R_MD,
)
 
PILL_H = 34
PILL_R = PILL_H // 2  # 17px
 
 
def _pill_normal_qss():
    return (
        "QPushButton {"
        f"  background: {BG_PILL};"
        f"  color: {TEXT_PRIMARY};"
        f"  border: 1.5px solid {BORDER};"
        f"  border-radius: {PILL_R}px;"
        f"  min-height: {PILL_H}px;"
        f"  max-height: {PILL_H}px;"
        "  padding: 0 20px;"
        "  font-size: 14px;"
        "}"
        "QPushButton:hover {"
        f"  background: {BG_PILL_HOVER};"
        f"  border-color: {BORDER_FOCUS};"
        "}"
    )
 
 
def _pill_selected_qss():
    return (
        "QPushButton {"
        f"  background: {BG_PILL_SEL};"
        f"  color: {ACCENT_SOFT};"
        f"  border: 1.5px solid {ACCENT_SOFT};"
        f"  border-radius: {PILL_R}px;"
        f"  min-height: {PILL_H}px;"
        f"  max-height: {PILL_H}px;"
        "  padding: 0 20px;"
        "  font-size: 14px;"
        "  font-weight: 600;"
        "}"
    )
 
 
# ── 进度条 ──
 
class ProgressBarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total = 1; self.done = 0; self.current = 0
        self.setFixedHeight(6)
 
    def set_progress(self, done, current, total):
        self.done = done; self.current = current
        self.total = max(total, 1); self.update()
 
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); r = h / 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(PROGRESS_BG)); p.drawRoundedRect(0, 0, w, h, r, r)
        if self.done > 0:
            gw = max(int(w * self.done / self.total), 1)
            p.setBrush(QColor(PROGRESS_DONE)); p.drawRoundedRect(0, 0, gw, h, r, r)
        if self.current > self.done:
            gw = int(w * self.done / self.total)
            ow = int(w * self.current / self.total) - gw
            if ow > 0:
                p.setBrush(QColor(PROGRESS_CUR))
                p.drawRoundedRect(gw, 0, ow, h, r, r)
        p.end()
 
 
# ── 单条问答 ──
 
class QuestionBlock(QFrame):
    answer_changed = pyqtSignal(str, object)
 
    def __init__(self, field, question, controller, parent=None):
        super().__init__(parent)
        self.field = field
        self.question = question
        self.controller = controller
        self._selected_key = None
        self.setStyleSheet("background: transparent;")
        self.buttons: List[QPushButton] = []
        self._build()
 
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
 
        # 问题卡片
        card = QFrame()
        card.setObjectName("qc")
        card.setStyleSheet(
            f"QFrame#qc {{ background: {BG_QUESTION}; border: none; border-radius: 16px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 14, 20, 14)
        lbl = QLabel(self.question.text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; background: transparent;")
        cl.addWidget(lbl)
        lay.addWidget(card)
 
        # 选项药丸
        row = QHBoxLayout()
        row.setContentsMargins(4, 4, 0, 4)
        row.setSpacing(10)
        for opt in self.question.options:
            btn = QPushButton(opt.label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(PILL_H)
            btn.setMaximumHeight(PILL_H)
            btn.setProperty("okey", opt.key)
            btn.setStyleSheet(_pill_normal_qss())
            btn.clicked.connect(lambda _, k=opt.key: self._click(k))
            row.addWidget(btn)
            self.buttons.append(btn)
        row.addStretch(1)
        rw = QWidget()
        rw.setStyleSheet("background: transparent;")
        rw.setLayout(row)
        lay.addWidget(rw)
 
        # 手动输入行（默认隐藏）
        self._manual_row = QWidget()
        self._manual_row.setStyleSheet("background: transparent;")
        mr = QHBoxLayout(self._manual_row)
        mr.setContentsMargins(4, 0, 0, 0)
        mr.setSpacing(8)
        self._manual_input = QLineEdit()
        self._manual_input.setPlaceholderText("请输入自定义内容…")
        self._manual_input.returnPressed.connect(self._manual_submit)
        mr.addWidget(self._manual_input, 1)
        cb = QPushButton("确认")
        cb.setCursor(Qt.PointingHandCursor)
        cb.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: {TEXT_ON_ACCENT}; border: none;"
            f"  border-radius: {R_MD}; padding: 8px 16px; font-weight: 600; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
        )
        cb.clicked.connect(self._manual_submit)
        mr.addWidget(cb)
        self._manual_row.setVisible(False)
        lay.addWidget(self._manual_row)
 
    def _click(self, key):
        self._selected_key = key
        for b in self.buttons:
            if b.property("okey") == key:
                b.setStyleSheet(_pill_selected_qss())
            else:
                b.setStyleSheet(_pill_normal_qss())
 
        if key == "other":
            self._manual_row.setVisible(True)
            self._manual_input.setFocus()
        else:
            self._manual_row.setVisible(False)
            ans = self.controller.questionnaire.engine._normalize_answer(
                self.question, {"selected": key}
            )
            self.answer_changed.emit(self.field, ans)
 
    def _manual_submit(self):
        t = self._manual_input.text().strip()
        if not t:
            return
        ans = self.controller.questionnaire.engine._normalize_answer(
            self.question, {"selected": "other", "manual_input": t}
        )
        self.answer_changed.emit(self.field, ans)
 
 
# ── 问答主体 ──
 
class ChatQuestionnaireWidget(QFrame):
    questionnaire_completed = pyqtSignal(dict)
    progress_changed = pyqtSignal(int, int, int)
 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = None
        self.fields: List[str] = []
        self.required_fields: List[str] = []
        self.blocks: List[QuestionBlock] = []
        self.answers: Dict[str, Any] = {}
        self._is_complete = False
        self._shown = 0
        self._setup()
 
    @property
    def is_complete(self):
        return self._is_complete
 
    def get_answers(self):
        return dict(self.answers)
 
    def _setup(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent;")
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.flow = QVBoxLayout(self.container)
        self.flow.setContentsMargins(0, 4, 0, 4)
        self.flow.setSpacing(14)
        self.flow.addStretch(1)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)
 
    def start_session(self, fields, req, ctrl):
        self.controller = ctrl
        self.fields = list(fields)
        self.required_fields = list(req)
        self.blocks = []
        self.answers = {}
        self._is_complete = False
        self._shown = 0
        self._clear()
        self._show_next()
 
    def _clear(self):
        while self.flow.count() > 1:
            it = self.flow.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        self.blocks = []
 
    def _show_next(self):
        while self._shown < len(self.fields):
            f = self.fields[self._shown]
            q = self.controller.questionnaire.get_question(f)
            if q is None:
                self._shown += 1
                continue
            blk = QuestionBlock(f, q, self.controller)
            blk.answer_changed.connect(self._on_ans)
            self.flow.insertWidget(self.flow.count() - 1, blk)
            self.blocks.append(blk)
            self._shown += 1
            QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()))
            self._emit()
            return
        self._check()
 
    def _on_ans(self, field, val):
        self.answers[field] = val
        self._is_complete = False
        idx = self.fields.index(field)
        if idx + 1 >= self._shown and self._shown < len(self.fields):
            self._show_next()
        else:
            self._check()
        self._emit()
 
    def _check(self):
        if self._shown >= len(self.fields):
            ok = all(
                f in self.answers
                for f in self.fields
                if self.controller.questionnaire.get_question(f) is not None
            )
            if ok and not self._is_complete:
                self._is_complete = True
                self.questionnaire_completed.emit(dict(self.answers))
        self._emit()
 
    def _emit(self):
        ans = len(self.answers)
        tot = sum(1 for f in self.fields
                  if self.controller.questionnaire.get_question(f) is not None)
        self.progress_changed.emit(ans, self._shown, tot)