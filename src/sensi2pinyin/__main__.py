"""sensi2pinyin 命令行：
- 交互输入路径（若未提供参数）
- 支持对 .txt 文件内容进行敏感词替换为拼音
- 可选择是否递归、是否原地覆盖、输出风格等
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from charset_normalizer import from_bytes

from .processor import replace_sensitive_to_pinyin

app = typer.Typer(add_completion=False, help="敏感词转拼音（txt处理/交互路径）")


def _read_text_file(path: Path, encoding: Optional[str] = None) -> tuple[str, str]:
    """
    读取文本，返回 (文本内容, 使用的编码)
    若 encoding 未提供，自动探测。
    """
    if encoding:
        text = path.read_text(encoding=encoding, errors="ignore")
        return text, encoding
    data = path.read_bytes()
    best = from_bytes(data).best()
    if best is None:
        # 回退 utf-8
        return data.decode("utf-8", errors="ignore"), "utf-8"
    return str(best), best.encoding or "utf-8"


@app.command()
def run(
    path: Optional[str] = typer.Argument(None, help="要处理的文件或目录（留空则进入交互输入）"),
    style: str = typer.Option("default", help="拼音风格: default|tone|first_letter|initials|finals"),
    recursive: bool = typer.Option(True, help="目录处理时是否递归"),
    inplace: bool = typer.Option(True, help="是否原地覆盖写回文件"),
    suffix: str = typer.Option(".pinyin", help="非覆盖写入时输出文件名后缀"),
    encoding: Optional[str] = typer.Option(None, help="指定读取/写入编码（默认自动探测并沿用）"),
    dry_run: bool = typer.Option(False, help="仅预览替换结果，不写入文件"),
) -> None:
    """执行敏感词替换。"""
    # 交互输入路径
    if not path:
        path = typer.prompt("请输入要处理的文件或文件夹路径")
    target = Path(path).expanduser().resolve()

    if not target.exists():
        logger.error(f"路径不存在: {target}")
        raise typer.Exit(code=2)

    files: list[Path] = []
    if target.is_file():
        if target.suffix.lower() == ".txt":
            files = [target]
        else:
            logger.error("仅支持处理 .txt 文本文件。")
            raise typer.Exit(code=2)
    else:
        globber = target.rglob if recursive else target.glob
        files = [p for p in globber("*.txt") if p.is_file()]

    if not files:
        logger.warning("未找到任何 .txt 文件。")
        raise typer.Exit(code=0)

    changed = 0
    for f in files:
        try:
            original, used_enc = _read_text_file(f, encoding)
            replaced = replace_sensitive_to_pinyin(original, style=style)
            if replaced != original:
                changed += 1
                logger.info(f"替换: {f}")
                if not dry_run:
                    if inplace:
                        f.write_text(replaced, encoding=encoding or used_enc, errors="ignore")
                    else:
                        out = f.with_suffix(f.suffix + suffix)
                        out.write_text(replaced, encoding=encoding or used_enc, errors="ignore")
            else:
                logger.debug(f"未检测到敏感词: {f}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"处理失败: {f} -> {e}")

    logger.success(f"处理完成，共扫描 {len(files)} 个文件，修改 {changed} 个。")


def main() -> None:  # 兼容 pyproject scripts 与 python -m 运行
    app()


if __name__ == "__main__":
    main()
