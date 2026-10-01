"""「分类设置」页面：两级分类的增删改。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from account_app import db


class CategoryPage(QWidget):
    # 分类有增删改时发出，供其他页面刷新分类下拉框
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._reload_tree()

    # ---------- 界面搭建 ----------

    def _build_ui(self) -> None:
        # 左侧：分类树
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self._update_buttons)

        # 右侧：操作按钮
        self.add_top_btn = QPushButton("➕ 加一级分类")
        self.add_sub_btn = QPushButton("➕ 加二级小类")
        self.rename_btn = QPushButton("✏️ 改名")
        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.setObjectName("danger")  # 删除是危险操作，用红色
        self.add_top_btn.clicked.connect(self._add_top)
        self.add_sub_btn.clicked.connect(self._add_sub)
        self.rename_btn.clicked.connect(self._rename)
        self.delete_btn.clicked.connect(self._delete)
        for b in (self.add_sub_btn, self.rename_btn, self.delete_btn):
            b.setEnabled(False)

        self.hint = QLabel(
            "规则：加一级分类 = 新增支出大类（收入保持一组，可给收入加小类）；"
            "分类下还有小类或账目时禁止删除；收支类型固定，只能改名。"
        )
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #666;")

        self.feedback = QLabel("")

        right = QVBoxLayout()
        right.addWidget(self.add_top_btn)
        right.addWidget(self.add_sub_btn)
        right.addWidget(self.rename_btn)
        right.addWidget(self.delete_btn)
        right.addStretch()

        main = QHBoxLayout()
        main.addWidget(self.tree, 3)
        main.addLayout(right, 1)

        layout = QVBoxLayout(self)  # 页面的主布局（唯一挂在 self 上的布局）
        layout.addLayout(main)
        layout.addWidget(self.hint)
        layout.addWidget(self.feedback)

    # ---------- 数据加载 ----------

    def _reload_tree(self) -> None:
        """重新加载分类树，并尽量保持原来选中的分类。"""
        selected_id = self._selected_id()
        self.tree.clear()
        for top in db.get_top_categories():
            item = QTreeWidgetItem([top["name"]])
            item.setData(0, Qt.ItemDataRole.UserRole, {"id": top["id"], "kind": top["kind"]})
            for sub in db.get_sub_categories(top["id"]):
                child = QTreeWidgetItem([sub["name"]])
                child.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"id": sub["id"], "kind": top["kind"]},
                )
                item.addChild(child)
            self.tree.addTopLevelItem(item)
        self.tree.expandAll()
        if selected_id is not None:
            self._select_item_by_id(selected_id)
        self._update_buttons()

    def _selected_id(self) -> int | None:
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole)["id"] if item else None

    def _select_item_by_id(self, category_id: int) -> None:
        """按分类 id 选中树里的条目。"""

        def walk(items) -> bool:
            for it in items:
                if it.data(0, Qt.ItemDataRole.UserRole)["id"] == category_id:
                    self.tree.setCurrentItem(it)
                    return True
                if walk([it.child(k) for k in range(it.childCount())]):
                    return True
            return False

        walk([self.tree.topLevelItem(k) for k in range(self.tree.topLevelItemCount())])

    def _update_buttons(self) -> None:
        """按当前选中情况开关按钮。"""
        item = self.tree.currentItem()
        has_sel = item is not None
        self.rename_btn.setEnabled(has_sel)
        self.delete_btn.setEnabled(has_sel)
        # 只有选中一级大类时才能加二级小类
        is_top = has_sel and item.parent() is None
        self.add_sub_btn.setEnabled(is_top)

    # ---------- 操作 ----------

    def _ask_name(self, title: str, label: str, default: str = "") -> str | None:
        """弹窗让用户输入分类名（确定/取消为中文按钮）。返回输入内容，取消返回 None。"""
        dlg = QInputDialog(self)
        dlg.setWindowTitle(title)
        dlg.setLabelText(label)
        dlg.setTextValue(default)
        dlg.setOkButtonText("确定")
        dlg.setCancelButtonText("取消")
        if dlg.exec() != QInputDialog.DialogCode.Accepted:
            return None
        name = dlg.textValue().strip()
        return name or None

    def _add_top(self) -> None:
        name = self._ask_name("新增一级分类", "分类名称（支出大类）：")
        if not name:
            return
        db.add_category(None, name, kind="expense")
        self._reload_tree()
        self._show_feedback(f"✓ 已新增一级分类「{name}」")
        self.changed.emit()

    def _add_sub(self) -> None:
        top_id = self._selected_id()
        if top_id is None:
            return
        item = self.tree.currentItem()
        top_name = item.text(0)
        name = self._ask_name("新增二级小类", f"「{top_name}」下的小类名称：")
        if not name:
            return
        kind = item.data(0, Qt.ItemDataRole.UserRole)["kind"]
        db.add_category(top_id, name, kind=kind)
        self._reload_tree()
        self._show_feedback(f"✓ 已新增小类「{name}」")
        self.changed.emit()

    def _rename(self) -> None:
        category_id = self._selected_id()
        if category_id is None:
            return
        old_name = self.tree.currentItem().text(0)
        name = self._ask_name("改名", "新名称：", default=old_name)
        if not name or name == old_name:
            return
        db.rename_category(category_id, name)
        self._reload_tree()
        self._show_feedback(f"✓ 已改名：「{old_name}」→「{name}」")
        self.changed.emit()

    def _delete(self) -> None:
        category_id = self._selected_id()
        if category_id is None:
            return
        name = self.tree.currentItem().text(0)
        # 先检查能不能删
        error = db.delete_category(category_id)
        if error:
            box = QMessageBox(self)
            box.setWindowTitle("不能删除")
            box.setText(f"「{name}」{error}")
            box.addButton("知道了", QMessageBox.ButtonRole.AcceptRole)
            box.exec()
            self._show_feedback("", ok=True)  # 清掉旧提示
            return
        self._reload_tree()
        self._show_feedback(f"✓ 已删除「{name}」")
        self.changed.emit()

    def _show_feedback(self, text: str, ok: bool = True) -> None:
        self.feedback.setStyleSheet("color: #2e7d32;" if ok else "color: #c62828;")
        self.feedback.setText(text)
