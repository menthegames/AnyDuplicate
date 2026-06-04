"""
Диалог пакетной обработки дубликатов
Позволяет выбрать действие для каждой группы и применить его массово.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox, QProgressBar,
    QCheckBox, QApplication
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QIcon
from core.i18n import tr
import os
import shutil


class BatchDialog(QDialog):
    """Диалог пакетной обработки дубликатов."""

    ACTIONS = {
        "keep": tr("batch.action_keep", "Оставить"),
        "delete": tr("batch.action_delete", "Удалить"),
        "move": tr("batch.action_move", "Переместить..."),
        "hardlink": tr("batch.action_hardlink", "Заменить hardlink'ом"),
    }

    def __init__(self, scanner, parent=None):
        super().__init__(parent)
        self.scanner = scanner
        self._results = {}  # group_hash -> action
        self._setup_ui()
        self._populate_groups()

    def _setup_ui(self):
        self.setWindowTitle(tr("batch.title", "Пакетная обработка дубликатов"))
        self.setMinimumSize(700, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel(tr("batch.header", "Пакетная обработка"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setStyleSheet("color: #E8E8ED;")
        layout.addWidget(title)

        desc = QLabel(
            tr("batch.description",
               "Выберите действие для каждой группы дубликатов. "
               "Действие будет применено ко всем файлам группы, кроме оригинала.")
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8B8B95; font-size: 12px;")
        layout.addWidget(desc)

        # Таблица групп
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "",
            tr("batch.header_group", "Группа"),
            tr("batch.header_files", "Файлов"),
            tr("batch.header_size", "Размер"),
            tr("batch.header_action", "Действие"),
        ])
        self.tree.setColumnWidth(0, 40)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 100)
        self.tree.setColumnWidth(4, 200)
        self.tree.header().setStretchLastSection(True)

        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #2A2A30;
                border-radius: 8px;
                background-color: #141416;
                alternate-background-color: #18181C;
                outline: none;
            }
            QTreeWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid #1E1E24;
                color: #C8C8D0;
                min-height: 28px;
            }
            QTreeWidget::item:selected {
                background-color: rgba(91, 143, 239, 0.2);
                color: #5B8FEF;
            }
            QHeaderView::section {
                background-color: #0A0A0C;
                color: #8B8B95;
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #2A2A30;
                font-weight: 600;
                font-size: 12px;
            }
        """)

        layout.addWidget(self.tree, 1)

        # Прогресс-бар (скрыт до начала выполнения)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E1E24;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                height: 20px;
                text-align: center;
                color: #E8E8ED;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #5B8FEF;
                border-radius: 7px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Кнопки
        btn_layout = QHBoxLayout()

        self.apply_btn = QPushButton(tr("batch.apply_btn", "Применить"))
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B8FEF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4A7DE0;
            }
            QPushButton:disabled {
                background-color: #2A2A32;
                color: #6A6A70;
            }
        """)
        self.apply_btn.clicked.connect(self._apply_actions)
        btn_layout.addWidget(self.apply_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton(tr("batch.cancel_btn", "Отмена"))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8B8B95;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #E8E8ED;
                border-color: #5B8FEF;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        # Стиль диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #0F0F12;
            }
            QComboBox {
                background-color: #1E1E24;
                color: #E8E8ED;
                border: 1px solid #2A2A30;
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 140px;
            }
            QComboBox:hover {
                border-color: #5B8FEF;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #141416;
                color: #E8E8ED;
                border: 1px solid #2A2A30;
                border-radius: 6px;
                selection-background-color: rgba(91, 143, 239, 0.2);
            }
        """)

    def _populate_groups(self):
        """Заполняет таблицу группами дубликатов."""
        self.tree.clear()

        if not self.scanner or not self.scanner.preview_data:
            return

        from core.utils import format_size

        # preview_data — список кортежей [(hash, original_path, [dup_paths, ...])]
        for group_idx, (hash_val, original, dups) in enumerate(self.scanner.preview_data, 1):
            all_files = [original] + dups

            # Групповой элемент
            group_item = QTreeWidgetItem()
            group_item.setText(0, "")
            group_item.setText(1, tr("results.group_label", "Группа {idx}").format(idx=group_idx))
            group_item.setText(2, str(len(all_files)))

            total_size = 0
            for f in all_files:
                try:
                    total_size += f.stat().st_size
                except Exception:
                    pass
            group_item.setText(3, format_size(total_size))

            group_item.setData(0, Qt.UserRole, hash_val)

            # Стиль группы
            group_font = QFont()
            group_font.setBold(True)
            group_item.setFont(1, group_font)
            group_item.setForeground(1, QColor("#5B8FEF"))

            self.tree.addTopLevelItem(group_item)

            # ComboBox с действиями
            combo = QComboBox()
            for key, label in self.ACTIONS.items():
                combo.addItem(label, key)
            combo.currentIndexChanged.connect(
                lambda idx, h=hash_val, c=combo: self._on_action_changed(h, c)
            )
            self.tree.setItemWidget(group_item, 4, combo)

            # Файлы в группе
            for file_path in all_files:
                file_item = QTreeWidgetItem()
                is_orig = (file_path == original)
                if is_orig:
                    file_item.setText(0, "★")
                    file_item.setToolTip(0, tr("batch.original_tooltip", "Этот файл является оригиналом — действие не применяется"))
                    file_item.setForeground(0, QColor("#FBBF24"))
                else:
                    file_item.setText(0, "")
                file_item.setText(1, "")
                file_item.setText(2, file_path.name)
                try:
                    file_item.setText(3, format_size(file_path.stat().st_size))
                except Exception:
                    file_item.setText(3, "—")
                file_item.setText(4, "")
                file_item.setForeground(2, QColor("#A0A0A8"))
                if is_orig:
                    file_item.setForeground(2, QColor("#FBBF24"))
                group_item.addChild(file_item)

        # Раскрываем первую группу
        if self.tree.topLevelItemCount() > 0:
            self.tree.topLevelItem(0).setExpanded(True)

    def _on_action_changed(self, hash_val: str, combo: QComboBox):
        """Сохраняет выбранное действие для группы."""
        action = combo.currentData()
        self._results[hash_val] = action

    def _apply_actions(self):
        """Применяет выбранные действия ко всем группам."""
        if not self._results:
            QMessageBox.information(
                self,
                tr("batch.no_actions", "Нет действий"),
                tr("batch.no_actions_detail", "Не выбрано ни одного действия.")
            )
            return

        # Подсчёт файлов для обработки
        total_actions = 0
        for hash_val, original, dups in self.scanner.preview_data:
            action = self._results.get(hash_val, "keep")
            if action != "keep":
                total_actions += len(dups)

        if total_actions == 0:
            QMessageBox.information(
                self,
                tr("batch.no_actions", "Нет действий"),
                tr("batch.no_actions_detail", "Не выбрано ни одного действия для обработки.")
            )
            return

        reply = QMessageBox.question(
            self,
            tr("batch.confirm_title", "Подтверждение"),
            tr("batch.confirm_text", "Будет обработано {n} файлов.\n\nПродолжить?").format(n=total_actions),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Выполнение
        self.apply_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total_actions)
        self.progress_bar.setValue(0)

        QApplication.processEvents()

        deleted = 0
        moved = 0
        hardlinked = 0
        errors = 0
        progress = 0

        for hash_val, original, dups in self.scanner.preview_data:
            action = self._results.get(hash_val, "keep")
            if action == "keep":
                continue

            orig_path = str(original) if original else None

            for dup_path in dups:
                dup_str = str(dup_path)
                if not dup_str or not os.path.exists(dup_str):
                    progress += 1
                    self.progress_bar.setValue(progress)
                    QApplication.processEvents()
                    continue

                try:
                    if action == "delete":
                        os.remove(dup_str)
                        deleted += 1
                    elif action == "move":
                        from PySide6.QtWidgets import QFileDialog
                        dest_dir = QFileDialog.getExistingDirectory(
                            self, tr("batch.move_dialog", "Выберите папку для перемещения")
                        )
                        if dest_dir:
                            dest_path = os.path.join(dest_dir, os.path.basename(dup_str))
                            shutil.move(dup_str, dest_path)
                            moved += 1
                    elif action == "hardlink":
                        if orig_path and os.path.exists(orig_path):
                            os.remove(dup_str)
                            os.link(orig_path, dup_str)
                            hardlinked += 1
                except Exception as e:
                    errors += 1

                progress += 1
                self.progress_bar.setValue(progress)
                QApplication.processEvents()

        self.progress_bar.setValue(self.progress_bar.maximum())

        # Итог
        msg_parts = []
        if deleted:
            msg_parts.append(tr("batch.result_deleted", "Удалено: {n}").format(n=deleted))
        if moved:
            msg_parts.append(tr("batch.result_moved", "Перемещено: {n}").format(n=moved))
        if hardlinked:
            msg_parts.append(tr("batch.result_hardlinked", "Заменено hardlink'ом: {n}").format(n=hardlinked))
        if errors:
            msg_parts.append(tr("batch.result_errors", "Ошибок: {n}").format(n=errors))

        QMessageBox.information(
            self,
            tr("batch.complete_title", "Пакетная обработка завершена"),
            "\n".join(msg_parts) if msg_parts else tr("batch.complete_empty", "Все действия выполнены.")
        )

        self.apply_btn.setEnabled(True)
        self.accept()
