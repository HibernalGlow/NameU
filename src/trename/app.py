"""trename Streamlit 界面

提供完整的可视化操作界面。
"""

import json
from pathlib import Path

import streamlit as st

from trename.clipboard import ClipboardHandler
from trename.models import (
    DirNode,
    FileNode,
    RenameJSON,
    RenameNode,
    count_pending,
    count_ready,
    count_total,
)
from trename.renamer import FileRenamer
from trename.scanner import FileScanner
from trename.undo import UndoManager
from trename.validator import ConflictValidator

# 页面配置
st.set_page_config(
    page_title="trename - 文件批量重命名",
    page_icon="📁",
    layout="wide",
)

# 初始化 session state
if "rename_json" not in st.session_state:
    st.session_state.rename_json = None
if "base_path" not in st.session_state:
    st.session_state.base_path = None
if "conflicts" not in st.session_state:
    st.session_state.conflicts = []
if "message" not in st.session_state:
    st.session_state.message = None


def render_node(
    node: RenameNode,
    parent_path: Path,
    conflict_paths: set,
    key_prefix: str,
) -> RenameNode:
    """渲染单个节点并返回更新后的节点"""
    if isinstance(node, FileNode):
        src_path = parent_path / node.src
        is_conflict = any(src_path == c[0] for c in conflict_paths)

        col1, col2, col3 = st.columns([3, 3, 1])

        with col1:
            st.text(f"📄 {node.src}")

        with col2:
            new_tgt = st.text_input(
                "目标名",
                value=node.tgt,
                key=f"{key_prefix}_tgt",
                label_visibility="collapsed",
                placeholder="输入目标文件名...",
            )

        with col3:
            if is_conflict:
                st.markdown("🔴 冲突")
            elif node.is_pending:
                st.markdown("🟡 待翻译")
            elif node.is_ready:
                st.markdown("🟢 就绪")
            else:
                st.markdown("⚪ 相同")

        return FileNode(src=node.src, tgt=new_tgt)

    else:  # DirNode
        src_path = parent_path / node.src_dir
        is_conflict = any(src_path == c[0] for c in conflict_paths)

        col1, col2, col3 = st.columns([3, 3, 1])

        with col1:
            st.text(f"📁 {node.src_dir}")

        with col2:
            new_tgt_dir = st.text_input(
                "目标名",
                value=node.tgt_dir,
                key=f"{key_prefix}_tgt",
                label_visibility="collapsed",
                placeholder="输入目标目录名...",
            )

        with col3:
            if is_conflict:
                st.markdown("🔴 冲突")
            elif node.is_pending:
                st.markdown("🟡 待翻译")
            elif node.is_ready:
                st.markdown("🟢 就绪")
            else:
                st.markdown("⚪ 相同")

        # 递归渲染子节点
        new_children = []
        with st.container():
            for i, child in enumerate(node.children):
                with st.container():
                    st.markdown(
                        "<div style='margin-left: 20px;'>",
                        unsafe_allow_html=True,
                    )
                    new_child = render_node(
                        child,
                        src_path,
                        conflict_paths,
                        f"{key_prefix}_{i}",
                    )
                    new_children.append(new_child)
                    st.markdown("</div>", unsafe_allow_html=True)

        return DirNode(
            src_dir=node.src_dir,
            tgt_dir=new_tgt_dir,
            children=new_children,
        )


def main():
    st.title("📁 trename - 文件批量重命名")

    # 侧边栏
    with st.sidebar:
        st.header("操作")

        # 扫描目录
        st.subheader("1. 扫描目录")
        scan_path = st.text_input(
            "目录路径",
            value=str(Path.cwd()),
            help="输入要扫描的目录路径",
        )

        if st.button("🔍 扫描目录", use_container_width=True):
            try:
                scanner = FileScanner()
                path = Path(scan_path)
                st.session_state.rename_json = scanner.scan(path)
                st.session_state.base_path = path
                st.session_state.conflicts = []
                st.session_state.message = ("success", f"扫描完成: {path}")
                st.rerun()
            except Exception as e:
                st.session_state.message = ("error", f"扫描失败: {e}")
                st.rerun()

        st.divider()

        # 导入 JSON
        st.subheader("2. 导入 JSON")

        if st.button("📋 从剪贴板粘贴", use_container_width=True):
            try:
                json_str = ClipboardHandler.paste()
                st.session_state.rename_json = RenameJSON.model_validate_json(json_str)
                st.session_state.message = ("success", "从剪贴板导入成功")
                st.rerun()
            except Exception as e:
                st.session_state.message = ("error", f"导入失败: {e}")
                st.rerun()

        uploaded_file = st.file_uploader("上传 JSON 文件", type=["json"])
        if uploaded_file:
            try:
                json_str = uploaded_file.read().decode("utf-8")
                st.session_state.rename_json = RenameJSON.model_validate_json(json_str)
                st.session_state.message = ("success", "文件导入成功")
                st.rerun()
            except Exception as e:
                st.session_state.message = ("error", f"导入失败: {e}")

        st.divider()

        # 导出
        st.subheader("3. 导出")

        if st.button("📤 复制到剪贴板", use_container_width=True):
            if st.session_state.rename_json:
                json_str = st.session_state.rename_json.model_dump_json(indent=2)
                ClipboardHandler.copy(json_str)
                st.session_state.message = ("success", "已复制到剪贴板")
                st.rerun()

        st.divider()

        # 撤销历史
        st.subheader("4. 撤销历史")
        undo_manager = UndoManager()
        history = undo_manager.get_history(limit=5)

        if history:
            for record in history:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"{record.id} ({len(record.operations)}项)")
                with col2:
                    if st.button("↩️", key=f"undo_{record.id}"):
                        result = undo_manager.undo(record.id)
                        st.session_state.message = (
                            "success",
                            f"撤销完成: {result.success_count} 成功",
                        )
                        st.rerun()
        else:
            st.text("暂无历史记录")

    # 主区域
    # 显示消息
    if st.session_state.message:
        msg_type, msg_text = st.session_state.message
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "error":
            st.error(msg_text)
        elif msg_type == "warning":
            st.warning(msg_text)
        st.session_state.message = None

    if st.session_state.rename_json is None:
        st.info("请先扫描目录或导入 JSON")
        return

    rename_json = st.session_state.rename_json

    # 操作按钮 - 移到顶部
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 检测冲突", use_container_width=True):
            if st.session_state.base_path:
                validator = ConflictValidator()
                conflicts = validator.validate(
                    st.session_state.rename_json,
                    st.session_state.base_path,
                )
                st.session_state.conflicts = conflicts
                if conflicts:
                    st.session_state.message = (
                        "warning",
                        f"检测到 {len(conflicts)} 个冲突",
                    )
                else:
                    st.session_state.message = ("success", "没有冲突")
                st.rerun()

    with col2:
        if st.button("▶️ 执行重命名", type="primary", use_container_width=True):
            if st.session_state.base_path:
                undo_manager = UndoManager()
                renamer = FileRenamer(undo_manager)
                result = renamer.rename_batch(
                    st.session_state.rename_json,
                    st.session_state.base_path,
                )
                st.session_state.message = (
                    "success",
                    f"重命名完成: {result.success_count} 成功, "
                    f"{result.failed_count} 失败, {result.skipped_count} 跳过",
                )
                # 重新扫描
                scanner = FileScanner()
                st.session_state.rename_json = scanner.scan(st.session_state.base_path)
                st.rerun()

    with col3:
        if st.button("↩️ 撤销最近操作", use_container_width=True):
            undo_manager = UndoManager()
            result = undo_manager.undo_latest()
            if result.success_count > 0:
                st.session_state.message = (
                    "success",
                    f"撤销完成: {result.success_count} 成功",
                )
                # 重新扫描
                if st.session_state.base_path:
                    scanner = FileScanner()
                    st.session_state.rename_json = scanner.scan(
                        st.session_state.base_path
                    )
            else:
                st.session_state.message = ("warning", "没有可撤销的操作")
            st.rerun()

    st.divider()

    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总项目", count_total(rename_json))
    with col2:
        st.metric("待翻译", count_pending(rename_json))
    with col3:
        st.metric("可重命名", count_ready(rename_json))
    with col4:
        st.metric("冲突", len(st.session_state.conflicts))

    # 显示冲突详情
    if st.session_state.conflicts:
        with st.expander(f"⚠️ 冲突详情 ({len(st.session_state.conflicts)})", expanded=True):
            for conflict in st.session_state.conflicts:
                st.warning(f"• {conflict.message}")

    st.divider()

    # 基础路径设置
    if st.session_state.base_path:
        base_path = st.text_input(
            "基础路径",
            value=str(st.session_state.base_path),
            help="重命名操作的基础路径",
        )
        st.session_state.base_path = Path(base_path)

    # 文件树编辑
    st.subheader("文件树")

    # 获取冲突路径
    conflict_paths = set()
    if st.session_state.base_path:
        validator = ConflictValidator()
        conflicts = validator.validate(rename_json, st.session_state.base_path)
        st.session_state.conflicts = conflicts
        conflict_paths = {(c.src_path, c.tgt_path) for c in conflicts}

    # 渲染文件树
    new_root = []
    for i, node in enumerate(rename_json.root):
        new_node = render_node(
            node,
            st.session_state.base_path or Path.cwd(),
            conflict_paths,
            f"node_{i}",
        )
        new_root.append(new_node)

    # 更新 session state
    st.session_state.rename_json = RenameJSON(root=new_root)

    # JSON 预览
    with st.expander("JSON 预览"):
        st.json(json.loads(st.session_state.rename_json.model_dump_json()))


if __name__ == "__main__":
    main()
