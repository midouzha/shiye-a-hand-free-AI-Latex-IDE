BG_BASE       = "#FAFAF8"
BG_SURFACE    = "#FFFFFF"
BG_SIDEBAR    = "#F5F1EB"
BG_QUESTION   = "#F7F5F1"
BG_PILL       = "#FFFFFF"
BG_PILL_HOVER = "#F5F1EB"
BG_PILL_SEL   = "#F5E0C2"

ACCENT        = "#D4860B"
ACCENT_HOVER  = "#B8740A"
ACCENT_LIGHT  = "#FDF3E3"
ACCENT_SOFT   = "#C5873A"

DOT_DONE    = "#5BA67A"
DOT_CURRENT = "#D4A44B"
DOT_PENDING = "#CCC6BD"
DOT_LINE    = "#D8D2C9"

PROGRESS_DONE = "#5BA67A"
PROGRESS_CUR  = "#D4A44B"
PROGRESS_BG   = "#E8E2D9"

TEXT_PRIMARY   = "#2C2520"
TEXT_SECONDARY = "#7A7166"
TEXT_TERTIARY  = "#A9A29A"
TEXT_ON_ACCENT = "#FFFFFF"

BORDER       = "#E8E2D9"
BORDER_LIGHT = "#F0ECE5"
BORDER_FOCUS = "#D4A44B"

R_SM = "6px"; R_MD = "10px"; R_LG = "14px"

SIDEBAR_W = 200
FONT = '"Microsoft YaHei","PingFang SC","Segoe UI",sans-serif'


def get_global_stylesheet():
    return f"""
    QMainWindow, QWidget#centralRoot {{
        background: {BG_BASE}; color: {TEXT_PRIMARY};
        font-family: {FONT}; font-size: 14px;
    }}
    QWidget#sidebar {{ background: {BG_SIDEBAR}; }}

    QLineEdit {{
        background: {BG_SURFACE}; border: 1px solid {BORDER};
        border-radius: {R_LG}; padding: 10px 14px;
        color: {TEXT_PRIMARY}; font-size: 14px;
    }}
    QLineEdit:focus {{ border-color: {BORDER_FOCUS}; }}

    QTextEdit {{
        background: {BG_BASE}; border: 1px solid {BORDER};
        border-radius: {R_MD}; padding: 10px 14px;
        color: {TEXT_PRIMARY}; font-size: 12px;
    }}

    QComboBox {{
        background: {BG_SURFACE}; border: 1px solid {BORDER};
        border-radius: {R_LG}; padding: 9px 14px; padding-right: 30px;
        color: {TEXT_PRIMARY}; font-size: 14px;
    }}
    QComboBox::drop-down {{ width: 28px; border: none; }}
    QComboBox::down-arrow {{
        width: 0; height: 0;
        border-left: 5px solid transparent; border-right: 5px solid transparent;
        border-top: 5px solid {TEXT_SECONDARY}; margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {BG_SURFACE}; border: 1px solid {BORDER};
        border-radius: {R_MD}; padding: 4px; outline: 0;
        selection-background-color: {BG_PILL_HOVER};
    }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 6px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 30px; border-radius: 3px; }}
    QScrollBar::handle:vertical:hover {{ background: {TEXT_TERTIARY}; }}
    QScrollBar:horizontal {{ background: transparent; height: 6px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {BORDER}; min-width: 30px; border-radius: 3px; }}
    QScrollBar::add-line, QScrollBar::sub-line,
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; border: none; }}

    QListWidget {{ background: transparent; border: none; outline: none; }}
    QListWidget::item {{
        background: {BG_SURFACE}; border: 1px solid {BORDER};
        border-radius: {R_MD}; padding: 8px 10px; margin-bottom: 4px; font-size: 12px;
    }}
    QListWidget::item:selected {{ background: {ACCENT_LIGHT}; border-color: {BORDER_FOCUS}; }}
    """