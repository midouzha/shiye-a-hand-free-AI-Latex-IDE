from datetime import datetime
from pathlib import Path
from typing import Dict, List

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.models.ui import UIState
from app.ui.generation_controller import GenerationController


class GenerationWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, controller: GenerationController, requirement: Dict[str, object], output_name: str) -> None:
        super().__init__()
        self.controller = controller
        self.requirement = requirement
        self.output_name = output_name

    def run(self) -> None:
        result = self.controller.run_with_requirement(self.requirement, output_name=self.output_name)
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.controller = GenerationController(project_root=project_root)
        self.state = UIState()
        self.worker = None

        self.setWindowTitle("师爷LaTeX排版工具")
        self.resize(1080, 720)

        self.template_selector = QComboBox()
        self.start_questionnaire_button = QPushButton("开始问答")
        self.prev_question_button = QPushButton("上一题")
        self.skip_question_button = QPushButton("跳过")
        self.next_question_button = QPushButton("下一题")
        self.generate_button = QPushButton("生成")
        self.status_label = QLabel("请先完成问答")

        self.question_title_label = QLabel("问答尚未开始")
        self.question_title_label.setWordWrap(True)
        self.option_selector = QComboBox()
        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText("若选择其他，请输入自定义内容")
        self.answers_preview = QTextEdit()
        self.answers_preview.setReadOnly(True)

        self.history_list = QListWidget()
        self.preview_label = QLabel("生成后将在这里显示 PDF 首页面预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(420)
        self.preview_label.setStyleSheet("border: 1px solid #d9e2ec; background: #ffffff;")
        self.preview_page_label = QLabel("第 0 / 0 页")
        self.preview_prev_button = QPushButton("上一页")
        self.preview_next_button = QPushButton("下一页")

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.summary_view = QTextEdit()
        self.summary_view.setReadOnly(True)

        self.questionnaire_fields: List[str] = []
        self.required_question_fields: List[str] = []
        self.questionnaire_index: int = 0
        self.answers_map: Dict[str, object] = {}
        self.current_pdf_path: str = ""
        self.current_page_index: int = 0
        self.current_page_count: int = 0

        self._build_ui()
        self._load_templates()
        self.start_questionnaire_button.clicked.connect(self.start_questionnaire)
        self.prev_question_button.clicked.connect(self.prev_question)
        self.skip_question_button.clicked.connect(self.skip_question)
        self.next_question_button.clicked.connect(self.next_question)
        self.generate_button.clicked.connect(self.handle_generate)
        self.history_list.itemClicked.connect(self._load_history_item)
        self.preview_prev_button.clicked.connect(self.preview_prev_page)
        self.preview_next_button.clicked.connect(self.preview_next_page)

        self.generate_button.setEnabled(False)
        self.next_question_button.setEnabled(False)
        self.prev_question_button.setEnabled(False)
        self.skip_question_button.setEnabled(False)
        self.preview_prev_button.setEnabled(False)
        self.preview_next_button.setEnabled(False)

    def _build_ui(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)

        title = QLabel("师爷LaTeX排版工具")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 700;")

        subtitle = QLabel("AI写内容，LaTeX管排版。")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #666;")

        status_banner = QLabel("当前模式：极简主界面 | 输入需求后点击生成")
        status_banner.setAlignment(Qt.AlignCenter)
        status_banner.setStyleSheet("padding: 8px; background: #f3f6fa; border: 1px solid #d9e2ec;")

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("模板"))
        toolbar.addWidget(self.template_selector, 1)
        toolbar.addWidget(self.start_questionnaire_button)
        toolbar.addWidget(self.prev_question_button)
        toolbar.addWidget(self.skip_question_button)
        toolbar.addWidget(self.next_question_button)
        toolbar.addWidget(self.generate_button)

        question_group = QGroupBox("Step2 问答区")
        question_layout = QVBoxLayout(question_group)
        question_layout.addWidget(self.question_title_label)
        question_layout.addWidget(self.option_selector)
        question_layout.addWidget(self.manual_input)
        question_layout.addWidget(QLabel("已采集答案"))
        question_layout.addWidget(self.answers_preview)

        preview_group = QGroupBox("PDF 预览区")
        preview_layout = QVBoxLayout(preview_group)
        preview_toolbar = QHBoxLayout()
        preview_toolbar.addWidget(self.preview_prev_button)
        preview_toolbar.addWidget(self.preview_next_button)
        preview_toolbar.addWidget(self.preview_page_label)
        preview_toolbar.addStretch(1)
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setWidget(self.preview_label)
        preview_layout.addLayout(preview_toolbar)
        preview_layout.addWidget(preview_scroll)

        history_group = QGroupBox("生成历史")
        history_layout = QVBoxLayout(history_group)
        history_layout.addWidget(self.history_list)
        history_layout.addWidget(QLabel("生成结果"))
        history_layout.addWidget(self.summary_view)

        body_splitter = QSplitter(Qt.Horizontal)
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.addWidget(question_group)
        left_layout.addWidget(QLabel("运行日志"))
        left_layout.addWidget(self.log_view)
        body_splitter.addWidget(left_container)
        body_splitter.addWidget(preview_group)
        body_splitter.addWidget(history_group)
        body_splitter.setSizes([420, 420, 260])

        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)
        root_layout.addWidget(status_banner)
        root_layout.addLayout(toolbar)
        root_layout.addWidget(body_splitter, 1)
        root_layout.addWidget(self.status_label)

        self.setCentralWidget(central)

    def _load_templates(self) -> None:
        templates = self.controller.available_templates() or ["default"]
        self.template_selector.clear()
        self.template_selector.addItems(templates)
        self.state.selected_template_id = templates[0]

    def start_questionnaire(self) -> None:
        required_fields = self.controller.questionnaire.get_question_fields()
        self.required_question_fields = list(required_fields)
        optional_fields = ["has_images", "has_tables", "references_required"]
        self.questionnaire_fields = list(required_fields)
        for field in optional_fields:
            if field not in self.questionnaire_fields and self.controller.questionnaire.get_question(field):
                self.questionnaire_fields.append(field)
        self.questionnaire_index = 0
        self.answers_map = {}
        self.state.questionnaire_step = 0
        self.state.questionnaire_total = len(self.questionnaire_fields)
        self.state.questionnaire_complete = False
        self.generate_button.setEnabled(False)
        self.next_question_button.setEnabled(True)
        self.prev_question_button.setEnabled(True)
        self.skip_question_button.setEnabled(True)
        self.status_label.setText("问答已开始，请选择答案后点击下一题")
        self._show_current_question()

    def _show_current_question(self) -> None:
        if self.questionnaire_index >= len(self.questionnaire_fields):
            self._finish_questionnaire()
            return

        field = self.questionnaire_fields[self.questionnaire_index]
        question = self.controller.questionnaire.get_question(field)
        if question is None:
            self.questionnaire_index += 1
            self._show_current_question()
            return

        self.question_title_label.setText(
            "[{0}/{1}] {2}".format(
                self.questionnaire_index + 1,
                len(self.questionnaire_fields),
                question.text,
            )
        )
        self.option_selector.clear()
        for option in question.options:
            self.option_selector.addItem(option.label, option.key)
        if field in self.answers_map:
            existing_answer = self.answers_map[field]
            matched_index = -1
            for idx, option in enumerate(question.options):
                if option.value == existing_answer:
                    matched_index = idx
                    break
            if matched_index >= 0:
                self.option_selector.setCurrentIndex(matched_index)
                self.manual_input.clear()
            else:
                other_index = self._find_option_index_by_key("other")
                self.option_selector.setCurrentIndex(other_index if other_index >= 0 else 0)
                self.manual_input.setText(str(existing_answer))
        else:
            self.manual_input.clear()

    def _find_option_index_by_key(self, key: str) -> int:
        for i in range(self.option_selector.count()):
            if self.option_selector.itemData(i) == key:
                return i
        return -1

    def prev_question(self) -> None:
        if not self.questionnaire_fields:
            return
        if self.questionnaire_index <= 0:
            self.status_label.setText("已经是第一题")
            return
        self.questionnaire_index -= 1
        self.state.questionnaire_step = self.questionnaire_index
        self.state.questionnaire_complete = False
        self.generate_button.setEnabled(False)
        self._show_current_question()

    def skip_question(self) -> None:
        if not self.questionnaire_fields or self.questionnaire_index >= len(self.questionnaire_fields):
            return
        field = self.questionnaire_fields[self.questionnaire_index]
        if field in self.required_question_fields:
            QMessageBox.information(self, "提示", "必填问题不能跳过。")
            return
        self.questionnaire_index += 1
        self.state.questionnaire_step = self.questionnaire_index
        self._show_current_question()

    def next_question(self) -> None:
        if self.questionnaire_index >= len(self.questionnaire_fields):
            self._finish_questionnaire()
            return

        field = self.questionnaire_fields[self.questionnaire_index]
        question = self.controller.questionnaire.get_question(field)
        if question is None:
            self.questionnaire_index += 1
            self._show_current_question()
            return

        selected_key = self.option_selector.currentData()
        manual_text = self.manual_input.text().strip()
        payload = {"selected": selected_key}
        if selected_key == "other" and manual_text:
            payload["manual_input"] = manual_text
        answer = self.controller.questionnaire.engine._normalize_answer(question, payload)

        if answer == "":
            QMessageBox.warning(self, "提示", "当前问题尚未填写有效答案。")
            return

        self.answers_map[field] = answer
        self.questionnaire_index += 1
        self.state.questionnaire_step = self.questionnaire_index
        self._refresh_answers_preview()
        self._show_current_question()

    def _finish_questionnaire(self) -> None:
        self.state.questionnaire_complete = True
        self.generate_button.setEnabled(True)
        self.next_question_button.setEnabled(False)
        self.prev_question_button.setEnabled(False)
        self.skip_question_button.setEnabled(False)
        self.question_title_label.setText("问答已完成，可点击生成")
        self.status_label.setText("问答完成，准备生成")

    def _refresh_answers_preview(self) -> None:
        lines = []
        for key in self.questionnaire_fields:
            if key in self.answers_map:
                lines.append("{0}: {1}".format(key, self.answers_map[key]))
        self.answers_preview.setPlainText("\n".join(lines))

    def _build_requirement(self) -> Dict[str, object]:
        template_id = self.template_selector.currentText().strip() or "default"
        requirement = dict(self.answers_map)
        requirement["template_id"] = template_id
        requirement.setdefault("has_images", False)
        requirement.setdefault("has_tables", False)
        requirement.setdefault("references_required", False)
        return requirement

    def handle_generate(self) -> None:
        if self.state.busy:
            return

        if not self.state.questionnaire_complete:
            QMessageBox.information(self, "提示", "请先完成 Step2 问答。")
            return

        requirement = self._build_requirement()
        self.state.busy = True
        self.state.error_message = ""
        self.status_label.setText("生成中...")
        self.generate_button.setEnabled(False)
        self.log_view.clear()
        self.summary_view.clear()

        self.worker = GenerationWorker(self.controller, requirement, output_name="ui_run")
        self.worker.finished.connect(self._handle_result)
        self.worker.start()

    def _handle_result(self, result) -> None:
        self.state.busy = False
        self.generate_button.setEnabled(True)
        self.state.last_message = result.message
        self.state.last_pdf_path = result.pdf_path
        self.state.last_tex_path = result.tex_path

        self.status_label.setText(result.message)
        if result.logs:
            self.log_view.setPlainText("\n".join(result.logs))
        if result.success:
            self.summary_view.setPlainText(
                "模板：{0}\nPDF：{1}\nTeX：{2}\nOutline：{3}".format(
                    self.template_selector.currentText(),
                    result.pdf_path,
                    result.tex_path,
                    " / ".join(result.outline) if result.outline else "-",
                )
            )
            self._append_history_item(result)
            self._set_preview_pdf(result.pdf_path)
        else:
            self.state.error_message = result.message
            self.summary_view.setPlainText(result.message)
            QMessageBox.warning(self, "生成失败", result.message)

    def _append_history_item(self, result) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        label = "{0} | {1}".format(ts, self.template_selector.currentText())
        payload = {
            "label": label,
            "pdf_path": result.pdf_path,
            "tex_path": result.tex_path,
            "message": result.message,
        }
        self.state.generated_items.append(payload)
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, payload)
        self.history_list.insertItem(0, item)
        self.history_list.setCurrentItem(item)

    def _load_history_item(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.UserRole) or {}
        self.summary_view.setPlainText(
            "{0}\nPDF：{1}\nTeX：{2}".format(
                payload.get("message", ""),
                payload.get("pdf_path", ""),
                payload.get("tex_path", ""),
            )
        )
        self._set_preview_pdf(payload.get("pdf_path", ""))

    def _set_preview_pdf(self, pdf_path: str) -> None:
        self.current_pdf_path = pdf_path
        self.current_page_index = 0
        self.current_page_count = self._read_pdf_page_count(pdf_path)
        self._update_preview_buttons()
        self._render_pdf_preview(pdf_path, self.current_page_index)

    def _read_pdf_page_count(self, pdf_path: str) -> int:
        if not pdf_path or not Path(pdf_path).exists():
            return 0
        try:
            import fitz

            document = fitz.open(pdf_path)
            count = int(document.page_count)
            document.close()
            return count
        except Exception:
            return 0

    def _update_preview_buttons(self) -> None:
        has_pdf = self.current_page_count > 0
        self.preview_prev_button.setEnabled(has_pdf and self.current_page_index > 0)
        self.preview_next_button.setEnabled(has_pdf and self.current_page_index < self.current_page_count - 1)
        if has_pdf:
            self.preview_page_label.setText("第 {0} / {1} 页".format(self.current_page_index + 1, self.current_page_count))
        else:
            self.preview_page_label.setText("第 0 / 0 页")

    def preview_prev_page(self) -> None:
        if self.current_page_count <= 0 or self.current_page_index <= 0:
            return
        self.current_page_index -= 1
        self._render_pdf_preview(self.current_pdf_path, self.current_page_index)
        self._update_preview_buttons()

    def preview_next_page(self) -> None:
        if self.current_page_count <= 0 or self.current_page_index >= self.current_page_count - 1:
            return
        self.current_page_index += 1
        self._render_pdf_preview(self.current_pdf_path, self.current_page_index)
        self._update_preview_buttons()

    def _render_pdf_preview(self, pdf_path: str, page_index: int = 0) -> None:
        if not pdf_path or not Path(pdf_path).exists():
            self.preview_label.setText("未找到 PDF 文件")
            self.preview_label.setPixmap(QPixmap())
            self.current_page_count = 0
            self.current_page_index = 0
            self._update_preview_buttons()
            return

        try:
            import fitz
        except Exception:
            self.preview_label.setText("未安装 PyMuPDF，无法内嵌预览。请安装后重试。")
            self.preview_label.setPixmap(QPixmap())
            return

        try:
            document = fitz.open(pdf_path)
            if page_index < 0 or page_index >= document.page_count:
                page_index = 0
            page = document.load_page(page_index)
            matrix = fitz.Matrix(1.3, 1.3)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            self.preview_label.setPixmap(QPixmap.fromImage(image.copy()))
            self.preview_label.setText("")
            self.current_page_count = int(document.page_count)
            self.current_page_index = page_index
            document.close()
            self._update_preview_buttons()
        except Exception as exc:
            self.preview_label.setText("PDF 预览失败: {0}".format(exc))
            self.preview_label.setPixmap(QPixmap())
