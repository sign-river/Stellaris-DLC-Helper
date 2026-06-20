#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""界面通用组件：区块标题、多行说明、图标按钮"""

from __future__ import annotations

import customtkinter as ctk


def _font_size_from_ctkfont(text_font, default: int = 14) -> int:
    if text_font is None:
        return default
    try:
        return int(text_font.cget("size"))
    except Exception:
        return default


def is_icon_button(btn) -> bool:
    """是否为 create_icon_button 创建的按钮（勿与 CTkButton 内部 _text_label 混淆）"""
    return getattr(btn, "_ib_text", None) is not None


def pack_section_header(
    parent,
    icon: str,
    title: str,
    *,
    icon_size: int = 20,
    title_size: int = 14,
    title_color: str = "#1976D2",
    bottom_padding: int = 8,
):
    """区块标题：左侧较大图标 + 右侧标题，垂直居中对齐"""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(anchor="w", fill="x", pady=(0, bottom_padding))

    line_height = max(icon_size, title_size) + 8

    icon_label = ctk.CTkLabel(
        row,
        text=icon,
        font=ctk.CTkFont(size=icon_size),
        text_color=title_color,
        width=icon_size + 12,
        height=line_height,
        anchor="center",
    )
    icon_label.grid(row=0, column=0, padx=(0, 8), sticky="w")

    title_label = ctk.CTkLabel(
        row,
        text=title,
        font=ctk.CTkFont(size=title_size, weight="bold"),
        text_color=title_color,
        height=line_height,
        anchor="w",
    )
    title_label.grid(row=0, column=1, sticky="w")

    return row, icon_label, title_label


def pack_description_lines(
    parent,
    lines,
    *,
    font_size: int = 12,
    text_color: str = "#666666",
    line_spacing: int = 10,
):
    """多行说明：拆成多行标签，增大行间距"""
    labels = []
    for index, line in enumerate(lines):
        bottom = line_spacing if index < len(lines) - 1 else 0
        label = ctk.CTkLabel(
            parent,
            text=line,
            font=ctk.CTkFont(size=font_size),
            text_color=text_color,
            anchor="w",
        )
        label.pack(anchor="w", pady=(0, bottom))
        labels.append(label)
    return labels


def create_icon_button(
    parent,
    icon: str,
    text: str,
    command,
    *,
    icon_size: int | None = None,
    text_font=None,
    width=130,
    height=45,
    **button_kwargs,
):
    """
    带图标的按钮：图标与文字分开展示，避免 emoji 与中文混排错位。
    可通过 update_icon_button() 更新文案。

    注意：不可使用 CTkButton 的 _text_label 属性名，否则重绘时会被销毁。
    """
    if text_font is None:
        text_font = ctk.CTkFont(size=14, weight="bold")

    text_size = _font_size_from_ctkfont(text_font, 14)
    if icon_size is None:
        icon_size = text_size + 4

    line_height = max(icon_size, text_size) + 6
    text_color = button_kwargs.get("text_color", "#FFFFFF")

    btn = ctk.CTkButton(
        parent,
        text="",
        command=command,
        width=width,
        height=height,
        **button_kwargs,
    )

    content = ctk.CTkFrame(btn, fg_color="transparent", height=line_height)
    content.pack_propagate(False)
    content.place(relx=0.5, rely=0.5, anchor="center")
    content.lift()

    icon_label = ctk.CTkLabel(
        content,
        text=icon,
        font=ctk.CTkFont(size=icon_size),
        text_color=text_color,
        width=icon_size + 12,
        height=line_height,
        anchor="center",
    )
    icon_label.grid(row=0, column=0, sticky="e")

    text_label = ctk.CTkLabel(
        content,
        text=text,
        font=text_font,
        text_color=text_color,
        height=line_height,
        anchor="w",
    )
    text_label.grid(row=0, column=1, padx=(8, 0), sticky="w")

    btn._ib_icon = icon_label
    btn._ib_text = text_label
    btn._ib_content = content
    btn._ib_text_color = text_color
    btn._ib_default_icon = icon
    btn._ib_default_text = text

    def _forward_click(_event=None):
        if str(btn.cget("state")) != "disabled":
            command()

    def _forward_enter(_event=None):
        btn._on_enter()

    def _forward_leave(_event=None):
        btn._on_leave()

    for widget in (content, icon_label, text_label):
        widget.bind("<Button-1>", _forward_click)
        widget.bind("<Enter>", _forward_enter)
        widget.bind("<Leave>", _forward_leave)

    return btn


def update_icon_button(btn, icon: str, text: str, *, text_color=None):
    """更新 create_icon_button 创建的按钮文案"""
    if not is_icon_button(btn):
        return

    color = text_color or getattr(btn, "_ib_text_color", "#FFFFFF")
    btn._ib_icon.configure(text=icon)
    btn._ib_text.configure(text=text, text_color=color)


def set_button_content(btn, *, icon: str | None = None, text: str | None = None, text_color=None):
    """统一更新普通按钮或图标按钮的显示文案"""
    if is_icon_button(btn):
        resolved_icon = icon if icon is not None else btn._ib_default_icon
        resolved_text = text if text is not None else btn._ib_default_text
        update_icon_button(btn, resolved_icon, resolved_text, text_color=text_color)
    elif text is not None:
        if icon:
            btn.configure(text=f"{icon} {text}".strip())
        else:
            btn.configure(text=text)
