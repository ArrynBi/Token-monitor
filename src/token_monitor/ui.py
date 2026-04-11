from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import math
from pathlib import Path
import queue
import sys
import threading

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QContextMenuEvent,
    QCursor,
    QFont,
    QIcon,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QRadialGradient,
    QRegion,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .config import ApiProfile, AppConfig, ConfigError, load_config, save_config
from .openai_api import OpenAIMonitorError, UsageSnapshot, fetch_snapshot
from .startup import StartupError, startup_supported, sync_launch_at_startup


APP_NAME = "Token悬浮球"
ORB_BG = QColor("#08111f")
ORB_CORE = QColor("#101a2d")
ORB_EDGE = QColor("#243a5d")
ORB_RING = QColor("#1b2b46")
ORB_PROGRESS = QColor("#8fb4ff")
TEXT = QColor("#edf4ff")
MUTED = QColor("#9cb0cd")
GOOD = QColor("#34d399")
WARN = QColor("#fbbf24")
BAD = QColor("#fb7185")
ACCENT = QColor("#ff8a3d")
ACCENT_SOFT = QColor("#ffb36c")
DETAIL_BG = "#0d1728"
DETAIL_PANEL = "#121f35"
LINE = "#233654"
DETAIL_WIDTH = 356
DETAIL_HEIGHT = 366
HELP_WIDTH = 420
HELP_HEIGHT = 390
ORB_MASK_INSET = 10


def _asset_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "assets" / name


def _load_app_icon() -> QIcon:
    icon_path = _asset_path("token_orb.svg")
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


APP_ICON = _load_app_icon()


def _format_compact_int(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def _format_usd(value: float, short: bool = False) -> str:
    if short:
        if value >= 100:
            return f"${value:.0f}"
        return f"${value:.1f}"
    if abs(value) < 10:
        return f"${value:.4f}"
    return f"${value:.2f}"


def _format_ms(milliseconds: float) -> str:
    if milliseconds <= 0:
        return "-"
    if milliseconds >= 1000:
        return f"{milliseconds / 1000:.1f}s"
    return f"{milliseconds:.0f}ms"


def _trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def _status_color(ratio: float, *, has_error: bool) -> QColor:
    if has_error:
        return BAD
    if ratio >= 0.95:
        return BAD
    if ratio >= 0.75:
        return WARN
    return GOOD


def _rgba(color: QColor, alpha: int) -> QColor:
    copy = QColor(color)
    copy.setAlpha(alpha)
    return copy


BASE_DIALOG_STYLE = f"""
QDialog {{
    background: transparent;
    color: {TEXT.name()};
}}
QFrame#shell {{
    background: {DETAIL_BG};
    border: 1px solid {LINE};
    border-radius: 22px;
}}
QFrame#panel {{
    background: {DETAIL_PANEL};
    border: 1px solid {LINE};
    border-radius: 16px;
}}
QFrame#titlebar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #172844, stop:0.72 #12203a, stop:1 #1a2740);
    border: none;
    border-top-left-radius: 22px;
    border-top-right-radius: 22px;
}}
QLabel[muted="true"] {{
    color: {MUTED.name()};
}}
QLabel[accent="true"] {{
    color: {ACCENT_SOFT.name()};
    font-weight: 700;
}}
QLabel[titlebar="true"] {{
    color: {TEXT.name()};
    font-weight: 700;
}}
QLineEdit {{
    background: {DETAIL_BG};
    color: {TEXT.name()};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 7px 10px;
    selection-background-color: {ACCENT.name()};
}}
QPushButton {{
    background: {ORB_CORE.name()};
    color: {TEXT.name()};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 7px 12px;
}}
QPushButton:hover {{
    border-color: {ACCENT.name()};
}}
QPushButton[accent="true"] {{
    background: {ACCENT.name()};
    color: #101010;
    border-color: {ACCENT.name()};
    font-weight: 700;
}}
QPushButton[titlebar="true"] {{
    background: qradialgradient(cx:0.35, cy:0.3, radius:0.92,
        fx:0.35, fy:0.3,
        stop:0 rgba(41, 68, 110, 240),
        stop:0.62 rgba(16, 26, 45, 238),
        stop:1 rgba(8, 17, 31, 245));
    color: {TEXT.name()};
    border: 1px solid rgba(143, 180, 255, 78);
    border-radius: 14px;
    padding: 0px;
}}
QPushButton[titlebar="true"]:hover {{
    border-color: {ACCENT.name()};
    background: qradialgradient(cx:0.35, cy:0.3, radius:0.92,
        fx:0.35, fy:0.3,
        stop:0 rgba(255, 179, 108, 235),
        stop:0.55 rgba(255, 138, 61, 230),
        stop:1 rgba(117, 58, 21, 220));
}}
QSizeGrip {{
    width: 16px;
    height: 16px;
}}
"""

MENU_STYLE = f"""
QMenu {{
    background: {DETAIL_PANEL};
    color: {TEXT.name()};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 22px;
    border-radius: 8px;
}}
QMenu::item:selected {{
    background: {ACCENT.name()};
    color: #101010;
}}
"""


class SettingsDialog(QDialog):
    def __init__(self, parent: "MonitorWindow", config: AppConfig) -> None:
        super().__init__(parent)
        self.setWindowFlags((self.windowFlags() | Qt.WindowType.FramelessWindowHint) & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setWindowTitle(f"{APP_NAME} 设置")
        self.setWindowIcon(APP_ICON)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(BASE_DIALOG_STYLE)
        self.setMinimumSize(520, 620)
        self.resize(config.window.settings_width, config.window.settings_height)
        self.result_config: AppConfig | None = None
        self.profile_editors: list[dict[str, object]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        shell = QFrame(objectName="shell")
        root.addWidget(shell)
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        title_bar = DialogTitleBar(self)
        shell_layout.addWidget(title_bar)

        body = QWidget()
        shell_layout.addWidget(body, 1)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel(f"{APP_NAME} 设置")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {TEXT.name()};")
        layout.addWidget(title)

        active_label = QLabel(f"当前启用: {config.current_profile.name}")
        active_label.setProperty("accent", True)
        layout.addWidget(active_label)

        hint = QLabel("API 列表支持添加多个配置。Base URL 只填主域名，不要带 /v1。")
        hint.setProperty("muted", True)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        layout.addWidget(scroll, 1)

        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        self.profile_layout = QVBoxLayout(scroll_content)
        self.profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_layout.setSpacing(10)

        for profile in config.profiles:
            self._add_profile_editor(profile)

        add_profile_button = QPushButton("+ 新增 API")
        add_profile_button.setProperty("accent", True)
        add_profile_button.clicked.connect(lambda: self._add_profile_editor())
        layout.addWidget(add_profile_button, alignment=Qt.AlignmentFlag.AlignLeft)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        layout.addLayout(form)

        self.fallback_budget = QLineEdit(str(config.fallback_budget_usd))
        self.refresh_interval = QLineEdit(str(config.refresh_interval_seconds))
        self.alpha = QLineEdit(str(config.window.alpha))
        self.launch_at_startup = QCheckBox("登录 Windows 时自动启动")
        self.launch_at_startup.setChecked(config.launch_at_startup)
        self.show_in_taskbar = QCheckBox("启动后在任务栏显示")
        self.show_in_taskbar.setChecked(config.window.show_in_taskbar)

        if not startup_supported():
            self.launch_at_startup.setEnabled(False)
            self.launch_at_startup.setToolTip("仅 Windows 支持开机启动")

        rows = [
            ("兜底额度（无明确额度时）", self.fallback_budget),
            ("刷新间隔", self.refresh_interval),
            ("窗口透明度", self.alpha),
        ]
        for label_text, widget in rows:
            label = QLabel(label_text)
            label.setProperty("muted", True)
            form.addRow(label, widget)

        startup_options = QWidget()
        startup_layout = QVBoxLayout(startup_options)
        startup_layout.setContentsMargins(0, 0, 0, 0)
        startup_layout.setSpacing(8)
        startup_layout.addWidget(self.launch_at_startup)
        startup_layout.addWidget(self.show_in_taskbar)
        startup_label = QLabel("启动选项")
        startup_label.setProperty("muted", True)
        form.addRow(startup_label, startup_options)

        self.message = QLabel("双击悬浮球展开详情，右键菜单和详情卡都可以一键切换 API。")
        self.message.setProperty("muted", True)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        buttons = QDialogButtonBox()
        cancel = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        save = buttons.addButton("保存", QDialogButtonBox.ButtonRole.AcceptRole)
        save.setProperty("accent", True)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._save)
        layout.addWidget(buttons)
        cancel.setAutoDefault(False)
        save.setAutoDefault(True)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch(1)
        size_grip = QSizeGrip(self)
        grip_row.addWidget(size_grip)
        layout.addLayout(grip_row)

        self._update_profile_editor_titles()

    def _add_profile_editor(self, profile: ApiProfile | None = None) -> None:
        profile = profile or ApiProfile(name=f"API {len(self.profile_editors) + 1}", base_url="", api_key="", organization_id="")
        section = QFrame(objectName="panel")
        self.profile_layout.addWidget(section)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        layout.addLayout(header)

        title = QLabel("API")
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {TEXT.name()};")
        header.addWidget(title)
        header.addStretch(1)

        remove_button = QPushButton("删除")
        remove_button.setFixedHeight(28)
        header.addWidget(remove_button)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        layout.addLayout(form)

        fields = {
            "name": QLineEdit(profile.name),
            "base_url": QLineEdit(profile.base_url),
            "api_key": QLineEdit(profile.api_key),
            "organization_id": QLineEdit(profile.organization_id),
        }
        fields["api_key"].setEchoMode(QLineEdit.EchoMode.Password)

        rows = [
            ("名称", fields["name"]),
            ("Base URL", fields["base_url"]),
            ("API Key", fields["api_key"]),
            ("组织 ID", fields["organization_id"]),
        ]
        for label_text, widget in rows:
            label = QLabel(label_text)
            label.setProperty("muted", True)
            form.addRow(label, widget)

        editor = {
            "widget": section,
            "title": title,
            "remove": remove_button,
            **fields,
        }
        self.profile_editors.append(editor)

        remove_button.clicked.connect(lambda: self._remove_profile_editor(editor))
        fields["name"].textChanged.connect(self._update_profile_editor_titles)
        self._update_profile_editor_titles()

    def _remove_profile_editor(self, editor: dict[str, object]) -> None:
        if len(self.profile_editors) <= 1:
            self.message.setText("至少保留一个 API 配置。")
            self.message.setStyleSheet(f"color: {BAD.name()};")
            return

        self.profile_editors.remove(editor)
        widget = editor["widget"]
        if isinstance(widget, QWidget):
            widget.hide()
            widget.deleteLater()
        self._update_profile_editor_titles()

    def _update_profile_editor_titles(self) -> None:
        for index, editor in enumerate(self.profile_editors):
            name_field = editor["name"]
            title = editor["title"]
            remove_button = editor["remove"]
            if not isinstance(name_field, QLineEdit) or not isinstance(title, QLabel) or not isinstance(remove_button, QPushButton):
                continue

            name = name_field.text().strip() or f"API {index + 1}"
            suffix = " · 当前" if index == self.parent().config.active_profile_index else ""
            title.setText(f"API {index + 1} · {name}{suffix}")
            remove_button.setEnabled(len(self.profile_editors) > 1)

    def _read_profile(self, fields: dict[str, object], index: int) -> ApiProfile | None:
        name_widget = fields["name"]
        base_widget = fields["base_url"]
        api_widget = fields["api_key"]
        org_widget = fields["organization_id"]
        if not all(isinstance(widget, QLineEdit) for widget in (name_widget, base_widget, api_widget, org_widget)):
            return None

        base_url = base_widget.text().strip().rstrip("/")
        api_key = api_widget.text().strip()
        organization_id = org_widget.text().strip()
        if not any((base_url, api_key, organization_id)):
            return None

        return ApiProfile(
            name=name_widget.text().strip() or f"API {index + 1}",
            base_url=base_url or "https://aixj.vip",
            api_key=api_key,
            organization_id=organization_id,
        )

    def _save(self) -> None:
        try:
            active_editor = self.profile_editors[min(self.parent().config.active_profile_index, len(self.profile_editors) - 1)]
            profiles: list[ApiProfile] = []
            active_profile_index = 0
            for index, editor in enumerate(self.profile_editors):
                profile = self._read_profile(editor, index)
                if profile is None:
                    continue
                if editor is active_editor:
                    active_profile_index = len(profiles)
                profiles.append(profile)

            if not profiles:
                self.message.setText("请至少填写一个可用的 API 配置。")
                self.message.setStyleSheet(f"color: {BAD.name()};")
                return

            updated = AppConfig(
                active_profile_index=min(active_profile_index, len(profiles) - 1),
                profiles=profiles,
                fallback_budget_usd=float(self.fallback_budget.text().strip() or 0),
                refresh_interval_seconds=max(30, int(self.refresh_interval.text().strip() or 300)),
                launch_at_startup=self.launch_at_startup.isChecked(),
                window=replace(
                    self.parent().config.window,
                    settings_width=max(520, self.width()),
                    settings_height=max(620, self.height()),
                    alpha=min(1.0, max(0.75, float(self.alpha.text().strip() or 0.98))),
                    show_in_taskbar=self.show_in_taskbar.isChecked(),
                ),
            )
        except ValueError:
            self.message.setText("请检查数字格式。")
            self.message.setStyleSheet(f"color: {BAD.name()};")
            return

        self.result_config = updated
        self.accept()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        parent = self.parent()
        if isinstance(parent, MonitorWindow):
            parent.config.window.settings_width = max(520, self.width())
            parent.config.window.settings_height = max(620, self.height())
            save_config(parent.config)
        super().closeEvent(event)


class DialogTitleBar(QFrame):
    def __init__(self, dialog: QDialog) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._drag_offset = QPoint()
        self.setObjectName("titlebar")
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 10, 4)
        layout.setSpacing(8)

        if not APP_ICON.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(APP_ICON.pixmap(16, 16))
            icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            layout.addWidget(icon_label)

        layout.addStretch(1)

        close_button = QPushButton("×")
        close_button.setProperty("titlebar", True)
        close_button.setFixedSize(14, 14)
        close_button.setToolTip("关闭")
        close_button.setStyleSheet(
            f"background: qradialgradient(cx:0.35, cy:0.3, radius:0.95,"
            f" fx:0.35, fy:0.3,"
            f" stop:0 rgba(255, 179, 108, 235),"
            f" stop:0.58 rgba(255, 138, 61, 228),"
            f" stop:1 rgba(126, 58, 18, 220));"
            f" color: #101010; border: 1px solid rgba(255, 212, 166, 190);"
            f" border-radius: 7px; font-size: 10px; font-weight: 700; padding: 0px;"
        )
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._dialog.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)


class HelpDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} 帮助")
        self.setWindowIcon(APP_ICON)
        self.setModal(False)
        self.setStyleSheet(BASE_DIALOG_STYLE)
        self.setFixedSize(HELP_WIDTH, HELP_HEIGHT)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        panel = QFrame(objectName="panel")
        root.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("帮助")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {TEXT.name()};")
        layout.addWidget(title)

        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        help_text.setFrameShape(QFrame.Shape.NoFrame)
        help_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        help_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        help_text.setStyleSheet(
            f"background: {DETAIL_BG}; color: {TEXT.name()}; border: 1px solid {LINE};"
            f" border-radius: 12px; padding: 10px; font-size: 12px;"
        )
        help_text.setHtml(
            "<div style='line-height:1.6;'>"
            "<b>剩余额度</b>: 当前还剩多少美元额度。<br>"
            "<b>今日已用</b>: 今天已经用了多少美元。<br>"
            "<b>请求次数</b>: 今天与累计的调用次数。<br>"
            "<b>Token 数</b>: 输入 / 输出 token 数。<br>"
            "<b>缓存读取</b>: 缓存命中的 token 读取数。<br>"
            "<b>TPM / RPM</b>: 每分钟 token / 请求数量。<br>"
            "<b>平均耗时</b>: 平均响应耗时。<br>"
            "<b>到期时间</b>: 套餐或订阅到期时间。<br><br>"
            "双击悬浮球展开或收起详情卡。<br>"
            "右键悬浮球可以刷新、切换 API、查看帮助、打开设置。"
            "</div>"
        )
        help_text.setReadOnly(True)
        layout.addWidget(help_text, 1)

        close_button = QPushButton("关闭")
        close_button.setProperty("accent", True)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)


class DetailPopup(QDialog):
    def __init__(self, owner: "MonitorWindow") -> None:
        super().__init__(owner)
        self.owner = owner
        self.setWindowIcon(APP_ICON)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(BASE_DIALOG_STYLE)
        self.setFixedSize(DETAIL_WIDTH, DETAIL_HEIGHT)
        self.labels: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        shell = QFrame(objectName="shell")
        root.addWidget(shell)

        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(10, 10, 10, 10)
        shell_layout.setSpacing(0)

        panel = QFrame(objectName="panel")
        shell_layout.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(11)

        header = QHBoxLayout()
        header.setSpacing(6)
        layout.addLayout(header)

        title = QLabel("用量详情")
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {TEXT.name()};")
        header.addWidget(title)
        header.addStretch(1)

        for text, tooltip, callback in (
            ("R", "刷新", owner.refresh_now),
            ("T", "切换 API", owner.open_profile_switch_menu),
            ("?", "帮助", owner.open_help),
            ("S", "设置", owner.open_settings),
            ("X", "关闭", owner.toggle_details),
        ):
            button = QPushButton(text)
            button.setToolTip(tooltip)
            button.setFixedSize(QSize(26, 26))
            button.setStyleSheet(
                f"background: {ORB_CORE.name()}; color: {TEXT.name()}; border: 1px solid {LINE};"
                f" border-radius: 9px; font-size: 11px; font-weight: 700; padding: 0px;"
            )
            button.clicked.connect(callback)
            header.addWidget(button)

        plan = QLabel("-")
        plan.setProperty("accent", True)
        plan.setWordWrap(True)
        plan.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {ACCENT_SOFT.name()};")
        layout.addWidget(plan)
        self.labels["plan"] = plan

        hero = QGridLayout()
        hero.setHorizontalSpacing(12)
        hero.setVerticalSpacing(10)
        hero.setColumnStretch(0, 1)
        hero.setColumnStretch(1, 1)
        layout.addLayout(hero)
        self.labels["remaining"] = self._metric(hero, "剩余额度", 0)
        self.labels["spent"] = self._metric(hero, "今日已用", 1)

        stats = QGridLayout()
        stats.setVerticalSpacing(9)
        stats.setHorizontalSpacing(14)
        stats.setColumnMinimumWidth(0, 74)
        stats.setColumnStretch(0, 0)
        stats.setColumnStretch(1, 1)
        layout.addLayout(stats)
        self.labels["requests"] = self._stat_line(stats, "请求次数", 0)
        self.labels["tokens"] = self._stat_line(stats, "Token 数", 1)
        self.labels["cache"] = self._stat_line(stats, "缓存读取", 2)
        self.labels["throughput"] = self._stat_line(stats, "TPM / RPM", 3)
        self.labels["latency"] = self._stat_line(stats, "平均耗时", 4)
        self.labels["expires"] = self._stat_line(stats, "到期时间", 5)
        self.labels["status"] = self._stat_line(stats, "状态", 6)

    def _metric(self, parent: QGridLayout, title: str, column: int) -> QLabel:
        card = QFrame()
        card.setStyleSheet(
            f"background: rgba(18, 31, 53, 235); border: none; border-radius: 14px;"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_label.setProperty("muted", True)
        title_label.setStyleSheet("font-size: 11px; font-weight: 600;")
        value = QLabel("-")
        value.setWordWrap(True)
        value.setStyleSheet(f"font-family: Consolas; font-size: 19px; font-weight: 700; color: {TEXT.name()};")
        layout.addWidget(title_label)
        layout.addWidget(value)
        parent.addWidget(card, 0, column)
        return value

    def _stat_line(self, parent: QGridLayout, title: str, row: int) -> QLabel:
        key = QLabel(title)
        key.setProperty("muted", True)
        key.setStyleSheet("font-size: 11px; font-weight: 600;")
        key.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        value = QLabel("-")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value.setStyleSheet(f"font-size: 11px; color: {TEXT.name()};")
        value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        parent.addWidget(key, row, 0)
        parent.addWidget(value, row, 1)
        return value


class MonitorWindow(QWidget):
    request_render = Signal()

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(APP_ICON)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.98)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._fetch_in_flight = False
        self._drag_offset = QPoint()
        self._detail_popup: DetailPopup | None = None
        self._help_popup: HelpDialog | None = None
        self._is_exiting = False
        self.snapshot: UsageSnapshot | None = None
        self.status_text = "等待中"
        self.status_color = MUTED

        try:
            self.config = load_config()
        except ConfigError as exc:
            self.config = AppConfig()
            self.status_text = str(exc)
            self.status_color = BAD

        self._apply_window_flags()
        self.setFixedSize(self.config.window.width, self.config.window.height)
        self.move(self.config.window.x, self.config.window.y)
        self.setWindowOpacity(self.config.window.alpha)
        self._apply_mask()
        self._build_menu()

        try:
            sync_launch_at_startup(self.config.launch_at_startup)
        except StartupError as exc:
            self.status_text = str(exc)
            self.status_color = BAD

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_queue)
        self._poll_timer.start(150)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self.refresh_now)

        QTimer.singleShot(250, self.refresh_now)

    def _window_flags(self) -> Qt.WindowType:
        flags = Qt.WindowType.FramelessWindowHint
        flags |= Qt.WindowType.Window if self.config.window.show_in_taskbar else Qt.WindowType.Tool
        if self.config.window.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        return flags

    def _apply_window_flags(self) -> None:
        was_visible = self.isVisible()
        position = self.pos()
        self.setWindowFlags(self._window_flags())
        self.move(position)
        self._apply_mask()
        if was_visible:
            self.show()
            self.raise_()

    def _build_menu(self) -> None:
        self.menu = QMenu(self)
        self.menu.setStyleSheet(MENU_STYLE)

        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_now)
        self.menu.addAction(refresh_action)

        self.switch_menu = self.menu.addMenu("切换 API")
        self.switch_menu.setStyleSheet(MENU_STYLE)
        self.switch_menu.aboutToShow.connect(lambda: self._populate_profile_menu(self.switch_menu))

        toggle_action = QAction("展开/收起详情", self)
        toggle_action.triggered.connect(self.toggle_details)
        self.menu.addAction(toggle_action)

        help_action = QAction("帮助", self)
        help_action.triggered.connect(self.open_help)
        self.menu.addAction(help_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.open_settings)
        self.menu.addAction(settings_action)
        self.menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(exit_action)

    def _profile_label(self, index: int, profile: ApiProfile) -> str:
        name = profile.name.strip() or f"API {index + 1}"
        return f"{name}  [{profile.base_url or '未填写地址'}]"

    def _populate_profile_menu(self, menu: QMenu) -> None:
        menu.clear()
        for index, profile in enumerate(self.config.profiles):
            action = QAction(self._profile_label(index, profile), menu)
            action.setCheckable(True)
            action.setChecked(index == self.config.active_profile_index)
            action.triggered.connect(lambda _checked=False, idx=index: self.set_active_profile(idx))
            menu.addAction(action)

        if not self.config.profiles:
            empty_action = QAction("还没有配置 API", menu)
            empty_action.setEnabled(False)
            menu.addAction(empty_action)

    def open_profile_switch_menu(self) -> None:
        popup = QMenu(self)
        popup.setStyleSheet(MENU_STYLE)
        self._populate_profile_menu(popup)
        anchor = QCursor.pos()
        if self._detail_popup is not None and self._detail_popup.isVisible():
            anchor = self._detail_popup.mapToGlobal(QPoint(self._detail_popup.width() - 10, 30))
        popup.exec(anchor)

    def _apply_mask(self) -> None:
        rect = self.rect().adjusted(ORB_MASK_INSET, ORB_MASK_INSET, -ORB_MASK_INSET, -ORB_MASK_INSET)
        self.setMask(QRegion(rect, QRegion.RegionType.Ellipse))

    def _draw_text(
        self,
        painter: QPainter,
        rect: QRectF,
        text: str,
        *,
        color: QColor,
        font: QFont,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
        shadow_alpha: int = 160,
    ) -> None:
        painter.save()
        painter.setFont(font)
        shadow = QColor(5, 11, 21, shadow_alpha)
        painter.setPen(shadow)
        painter.drawText(rect.translated(0, 1), int(align), text)
        painter.setPen(color)
        painter.drawText(rect, int(align), text)
        painter.restore()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        width = float(self.width())
        height = float(self.height())
        size = min(width, height)
        center_x = width / 2
        center_y = height / 2

        snapshot = self.snapshot
        ratio = snapshot.usage_ratio if snapshot is not None else 0.0
        indicator = _status_color(ratio, has_error=self.status_color == BAD and snapshot is None)

        core_radius = size * 0.35
        ring_radius = core_radius + 8
        shadow_radius = ring_radius + 20

        shadow_gradient = QRadialGradient(center_x, center_y + 6, shadow_radius)
        shadow_gradient.setColorAt(0.48, QColor(4, 8, 18, 86))
        shadow_gradient.setColorAt(0.82, QColor(4, 8, 18, 28))
        shadow_gradient.setColorAt(1.0, QColor(4, 8, 18, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow_gradient)
        painter.drawEllipse(QRectF(center_x - shadow_radius, center_y - shadow_radius + 6, shadow_radius * 2, shadow_radius * 2))

        shell_rect = QRectF(center_x - core_radius, center_y - core_radius, core_radius * 2, core_radius * 2)
        core_gradient = QRadialGradient(center_x - core_radius * 0.22, center_y - core_radius * 0.34, core_radius * 1.25)
        core_gradient.setColorAt(0.0, QColor(24, 36, 60, 248))
        core_gradient.setColorAt(0.64, QColor(16, 26, 45, 252))
        core_gradient.setColorAt(1.0, QColor(9, 15, 27, 255))
        painter.setBrush(core_gradient)
        painter.setPen(QPen(ORB_EDGE, 1.6))
        painter.drawEllipse(shell_rect)

        ring_rect = shell_rect.adjusted(9, 9, -9, -9)
        painter.setPen(QPen(ORB_RING, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(ring_rect, 90 * 16, -360 * 16)
        painter.setPen(QPen(ORB_PROGRESS, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        span = max(12, int(math.floor(360 * ratio))) if snapshot is not None else 20
        painter.drawArc(ring_rect, 90 * 16, -span * 16)

        painter.setPen(QPen(QColor("#0a1324"), 1.2))
        painter.setBrush(indicator)
        painter.drawEllipse(QRectF(center_x + 28, center_y - 34, 10, 10))

        remaining = _format_usd(snapshot.remaining_budget_usd, short=True) if snapshot is not None else "--"
        detail = "今日剩余" if snapshot is not None else _trim(self.status_text, 12)
        micro = "同步中" if self._fetch_in_flight else _trim(self.status_text, 10)
        bottom_left = f"{snapshot.request_count} 次" if snapshot is not None else "双击详情"
        bottom_right = f"{int(ratio * 100)}%" if snapshot is not None else micro

        self._draw_text(
            painter,
            QRectF(center_x - 54, center_y - 26, 108, 28),
            remaining,
            color=TEXT,
            font=QFont("Segoe UI", 18, QFont.Weight.Bold),
        )
        self._draw_text(
            painter,
            QRectF(center_x - 54, center_y + 1, 108, 16),
            detail,
            color=MUTED,
            font=QFont("Segoe UI", 7, QFont.Weight.DemiBold),
        )
        self._draw_text(
            painter,
            QRectF(center_x - 38, center_y + 21, 46, 16),
            bottom_left,
            color=TEXT,
            font=QFont("Segoe UI", 6, QFont.Weight.Bold),
            align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        self._draw_text(
            painter,
            QRectF(center_x + 2, center_y + 21, 36, 16),
            bottom_right,
            color=TEXT if snapshot is not None else MUTED,
            font=QFont("Consolas", 7, QFont.Weight.Bold),
            align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            self._position_detail_popup()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.config.window.x = self.x()
            self.config.window.y = self.y()
            save_config(self.config)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_details()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.menu.exec(event.globalPos())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._apply_mask()
        super().resizeEvent(event)

    def toggle_details(self) -> None:
        if self._detail_popup is not None and self._detail_popup.isVisible():
            self._detail_popup.hide()
            return

        if self._detail_popup is None:
            self._detail_popup = DetailPopup(self)
        self._position_detail_popup()
        self._update_detail_popup()
        self._detail_popup.show()
        self._detail_popup.raise_()

    def _position_detail_popup(self) -> None:
        if self._detail_popup is None:
            return

        x = self.x() + self.width() + 12
        y = self.y() + 10
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            if x + DETAIL_WIDTH > available.right():
                x = self.x() - DETAIL_WIDTH - 12
            if y + DETAIL_HEIGHT > available.bottom():
                y = available.bottom() - DETAIL_HEIGHT
        self._detail_popup.move(x, y)

    def open_help(self) -> None:
        if self._help_popup is None:
            self._help_popup = HelpDialog(self)
            self._help_popup.finished.connect(self._clear_help_popup)
        self._help_popup.move(self.x() + self.width() + 18, self.y() + 22)
        self._help_popup.show()
        self._help_popup.raise_()
        self._help_popup.activateWindow()

    def _clear_help_popup(self) -> None:
        self._help_popup = None

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, self.config)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result_config is None:
            return

        updated_config = dialog.result_config
        try:
            sync_launch_at_startup(updated_config.launch_at_startup)
        except StartupError as exc:
            self._set_status(str(exc), BAD)
            return

        flags_changed = (
            updated_config.window.show_in_taskbar != self.config.window.show_in_taskbar
            or updated_config.window.always_on_top != self.config.window.always_on_top
        )
        self.config = updated_config
        self.snapshot = None
        save_config(self.config)
        if flags_changed:
            self._apply_window_flags()
        self.setWindowOpacity(self.config.window.alpha)
        self._set_status("配置已保存，正在刷新...", MUTED)
        self.refresh_now()

    def set_active_profile(self, index: int) -> None:
        if index < 0 or index >= len(self.config.profiles):
            return

        target = self.config.profiles[index]
        if not target.base_url or not target.api_key:
            self._set_status("请先在设置里完善这个 API 配置。", BAD)
            return

        if index == self.config.active_profile_index:
            self._set_status(f"当前已是 {self.config.current_profile.name}。", MUTED)
            return

        self.config.active_profile_index = index
        self.snapshot = None
        save_config(self.config)
        self._set_status(f"已切换到 {self.config.current_profile.name}，正在刷新...", MUTED)
        self.refresh_now()

    def exit_app(self) -> None:
        if self._is_exiting:
            return

        self._is_exiting = True
        self._poll_timer.stop()
        self._refresh_timer.stop()
        self._fetch_in_flight = False

        if self.menu.isVisible():
            self.menu.hide()
        self.menu.close()
        self.menu.deleteLater()

        for popup_name in ("_detail_popup", "_help_popup"):
            popup = getattr(self, popup_name)
            if popup is not None:
                popup.hide()
                popup.close()
                popup.deleteLater()
                setattr(self, popup_name, None)

        self.hide()
        self.close()

        app = QApplication.instance()
        if app is not None:
            app.closeAllWindows()
            app.quit()

    def refresh_now(self) -> None:
        if self._fetch_in_flight:
            return

        self._fetch_in_flight = True
        self._set_status("同步中...", MUTED)
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self) -> None:
        try:
            snapshot = fetch_snapshot(self.config)
        except OpenAIMonitorError as exc:
            self._queue.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001
            self._queue.put(("error", f"未预期错误: {exc}"))
        else:
            self._queue.put(("snapshot", snapshot))
        finally:
            self._queue.put(("done", None))

    def _poll_queue(self) -> None:
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                break

            if kind == "snapshot":
                self._apply_snapshot(payload)  # type: ignore[arg-type]
            elif kind == "error":
                self._set_status(str(payload), BAD)
            elif kind == "done":
                self._fetch_in_flight = False
                self._schedule_next_refresh()

    def _apply_snapshot(self, snapshot: UsageSnapshot) -> None:
        self.snapshot = snapshot
        updated_at = datetime.now().strftime("%H:%M:%S")
        self._set_status(f"{self.config.current_profile.name} 已更新 {updated_at}", MUTED)

    def _update_detail_popup(self) -> None:
        if self._detail_popup is None:
            return

        labels = self._detail_popup.labels
        snapshot = self.snapshot
        if snapshot is None:
            labels["plan"].setText(f"{self.config.current_profile.name} · 等待数据")
            labels["remaining"].setText("--")
            labels["spent"].setText("--")
            labels["requests"].setText("-")
            labels["tokens"].setText("-")
            labels["cache"].setText("-")
            labels["throughput"].setText("-")
            labels["latency"].setText("-")
            labels["expires"].setText("-")
            labels["status"].setText(self.status_text)
            labels["status"].setStyleSheet(f"font-size: 12px; color: {self.status_color.name()};")
            return

        labels["plan"].setText(f"{self.config.current_profile.name} · {snapshot.plan_name or snapshot.source_label}")
        labels["remaining"].setText(_format_usd(snapshot.remaining_budget_usd))
        labels["remaining"].setStyleSheet(
            f"font-family: Consolas; font-size: 20px; font-weight: 700; color: {(GOOD if snapshot.remaining_budget_usd >= 0 else BAD).name()};"
        )
        labels["spent"].setText(_format_usd(snapshot.period_cost_usd))
        labels["spent"].setStyleSheet(
            f"font-family: Consolas; font-size: 20px; font-weight: 700; color: {ACCENT_SOFT.name()};"
        )
        labels["requests"].setText(f"{_format_compact_int(snapshot.request_count)} 今日 | {_format_compact_int(snapshot.overall_request_count)} 累计")
        labels["tokens"].setText(f"{_format_compact_int(snapshot.input_tokens)} 输入 | {_format_compact_int(snapshot.output_tokens)} 输出")
        labels["cache"].setText(_format_compact_int(snapshot.cached_tokens))
        labels["throughput"].setText(f"{_format_compact_int(snapshot.tpm)} / {_format_compact_int(snapshot.rpm)}")
        labels["latency"].setText(_format_ms(snapshot.average_duration_ms))
        expires = snapshot.expires_at.strftime("%m-%d %H:%M") if snapshot.expires_at is not None else "-"
        labels["expires"].setText(expires)
        labels["status"].setText(self.status_text)
        labels["status"].setStyleSheet(f"font-size: 12px; color: {self.status_color.name()};")

    def _schedule_next_refresh(self) -> None:
        self._refresh_timer.start(self.config.refresh_interval_seconds * 1000)

    def _set_status(self, message: str, color: QColor) -> None:
        self.status_text = message
        self.status_color = color
        self._update_detail_popup()
        self.update()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._is_exiting = True
        self._poll_timer.stop()
        self._refresh_timer.stop()
        if self._detail_popup is not None:
            self._detail_popup.close()
        if self._help_popup is not None:
            self._help_popup.close()
        super().closeEvent(event)


def run_app() -> None:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    if not APP_ICON.isNull():
        app.setWindowIcon(APP_ICON)

    window = MonitorWindow()
    window.show()

    if owns_app:
        app.exec()
