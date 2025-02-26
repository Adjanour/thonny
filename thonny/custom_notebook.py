from __future__ import annotations

import os.path
import sys
import tkinter as tk
from logging import getLogger
from tkinter import ttk
from typing import List, Literal, Optional, Union

from thonny.languages import tr
from thonny.misc_utils import running_on_mac_os

logger = getLogger(__name__)

if sys.platform == "win32":
    border_color = "system3dLight"
    frame_background = "systemButtonFace"
    activeTabBackground = "systemWindow"
    active_indicator_color = "systemHighlight"
elif sys.platform == "darwin":
    activeTabBackground = "systemTextBackgroundColor"
    frame_background = "systemWindowBackgroundColor"
    border_color = "systemWindowBackgroundColor7"
    active_indicator_color = "systemLinkColor"


class CustomNotebook(tk.Frame):
    def __init__(self, master: Union[tk.Widget, tk.Toplevel, tk.Tk], closable: bool = True):
        super().__init__(master, background=border_color)
        self.closable = closable
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Can't use ttk.Frame, because can't change it's color in aqua
        self.tab_row = tk.Frame(self, background=border_color)
        self.tab_row.grid(row=0, column=0, sticky="new")

        self.filler = tk.Frame(self.tab_row, background=frame_background)
        self.filler.grid(row=0, column=999, sticky="nsew", padx=(1, 0), pady=(0, 1))
        self.tab_row.columnconfigure(999, weight=1)

        self.current_page: Optional[CustomNotebookPage] = None
        self.pages: List[CustomNotebookPage] = []

    def add(self, child: tk.Widget, text: str) -> None:
        self.insert("end", child, text=text)

    def insert(self, pos: Union[int, Literal["end"]], child: tk.Widget, text: str) -> None:
        tab = CustomNotebookTab(self, title=text, closable=self.closable)
        page = CustomNotebookPage(tab, child)
        if pos == "end":
            self.pages.append(page)
        else:
            self.pages.insert(pos, page)

        self._rearrange_tabs()
        self.select_tab(page.tab)

    def _rearrange_tabs(self) -> None:
        for i, page in enumerate(self.pages):
            page.tab.grid(row=0, column=i, sticky="nsew", padx=(1, 0), pady=(1, 0))

    def enable_traversal(self) -> None:
        # TODO:
        pass

    def select(self, tab_id: Union[str, tk.Widget, None] = None) -> Optional[str]:
        if tab_id is None:
            if self.current_page:
                return self.current_page.content.winfo_name()
            return None

        return self.select_by_index(self.index(tab_id))

    def select_by_index(self, index: int) -> None:
        new_page = self.pages[index]
        if new_page == self.current_page:
            return

        new_page.content.grid_propagate(False)
        new_page.content.grid(row=1, column=0, sticky="nsew", padx=(1, 1), pady=(0, 1))
        new_page.content.tkraise()

        new_page.tab.update_state(True)
        if self.current_page:
            self.current_page.tab.update_state(False)

        self.current_page = new_page
        self.event_generate("<<NotebookTabChanged>>")  # TODO:

    def select_tab(self, tab: CustomNotebookTab) -> None:
        for i, page in enumerate(self.pages):
            if page.tab == tab:
                self.select_by_index(i)
                return

        raise ValueError(f"Unknown tab {tab}")

    def index(self, tab_id: Optional[str, tk.Widget]) -> int:
        if tab_id == "end":
            return len(self.pages)

        for i, page in enumerate(self.pages):
            if page.content == tab_id or page.content.winfo_name() == tab_id:
                return i
        else:
            raise RuntimeError(f"Can't find {tab_id!r}")

    def tab(self, tab_id: Union[str, tk.Widget], text: str):
        page = self.pages[self.index(tab_id)]
        page.tab.set_title(text)

    def tabs(self) -> List[str]:
        return [page.content.winfo_name() for page in self.pages]

    def winfo_children(self) -> List[tk.Widget]:
        return [page.content for page in self.pages]

    def forget(self, child: tk.Widget) -> None:
        for i, page in enumerate(self.pages):
            if child is page.content:
                break
        else:
            raise ValueError(f"Can't find {child}")

        self.pages[i].content.grid_forget()
        self.pages[i].tab.grid_forget()
        del self.pages[i]

        if len(self.pages) == 0:
            self.current_page = None
        elif len(self.pages) > i:
            self.current_page = self.pages[i]  # right neighbor of the deleted page
        else:
            self.current_page = self.pages[-1]  # last remaining page

        self._rearrange_tabs()

    def get_child_by_index(self, index: int) -> tk.Widget:
        return self.pages[index].content

    def get_current_child(self) -> Optional[tk.Widget]:
        if self.current_page:
            return self.current_page.content
        return None

    def focus_set(self):
        if self.current_page:
            self.current_page.content.focus_set()
        else:
            super().focus_set()

    def close_tab(self, tab: CustomNotebookTab) -> None:
        for page in self.pages:
            if page.tab == tab:
                self.forget(page.content)
                return
        else:
            raise ValueError(f"Can't find {tab}")

    def close_tabs(self, except_tab: Optional[CustomNotebookTab] = None):
        for page in reversed(self.pages):
            if page.tab == except_tab:
                continue
            else:
                self.close_tab(page.tab)


class CustomNotebookTab(tk.Frame):
    close_image = None
    active_close_image = None

    def __init__(self, notebook: CustomNotebook, title: str, closable: bool):
        from thonny import get_workbench
        from thonny.ui_utils import ems_to_pixels, get_style_configuration

        super().__init__(notebook.tab_row, borderwidth=0)
        self.notebook = notebook
        self.title = title
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.label = tk.Label(self, text=title)
        self.label.grid(
            row=0,
            column=0,
            padx=(ems_to_pixels(0.3), ems_to_pixels(0.1)),
            sticky="nsw",
            pady=(0, ems_to_pixels(0.1)),
        )
        self.bind("<1>", self.on_click, True)
        self.label.bind("<1>", self.on_click, True)

        if closable:
            if not CustomNotebookTab.close_image:
                CustomNotebookTab.close_image = get_workbench().get_image("tab-close")
                CustomNotebookTab.active_close_image = get_workbench().get_image("tab-close-active")
            self.button = tk.Label(self, image=CustomNotebookTab.close_image)
            self.button.grid(row=0, column=1, padx=(0, ems_to_pixels(0.1)))
            self.button.bind("<1>", self.on_button_click, True)
            self.button.bind("<Enter>", self.on_button_enter, True)
            self.button.bind("<Leave>", self.on_button_leave, True)

            if running_on_mac_os():
                self.label.bind("<ButtonPress-2>", self._right_btn_press, True)
                self.label.bind("<Control-Button-1>", self._right_btn_press, True)
                self.label.bind("<ButtonPress-3>", self._middle_btn_press, True)
            else:
                self.label.bind("<ButtonPress-3>", self._right_btn_press, True)
                self.label.bind("<ButtonPress-2>", self._middle_btn_press, True)

        else:
            self.button = None

        self.indicator = tk.Frame(self, height=1, background=border_color)
        self.indicator.grid(row=1, column=0, columnspan=2, sticky="sew")

        self.menu = tk.Menu(self.winfo_toplevel(), tearoff=False, **get_style_configuration("Menu"))
        self.menu.add_command(label=tr("Close"), command=self._close_tab)
        self.menu.add_command(label=tr("Close others"), command=self._close_other_tabs)
        self.menu.add_command(label=tr("Close all"), command=self._close_all_tabs)

    def set_title(self, text: str) -> None:
        self.label.configure(text=text)

    def _right_btn_press(self, event):
        self.menu.tk_popup(*self.winfo_toplevel().winfo_pointerxy())

    def _middle_btn_press(self, event):
        self._close_tab()

    def _close_tab(self) -> None:
        self.notebook.close_tab(self)

    def _close_all_tabs(self) -> None:
        self.notebook.close_tabs()

    def _close_other_tabs(self) -> None:
        self.notebook.close_tabs(except_tab=self)

    def on_click(self, event):
        self.notebook.select_tab(self)

    def on_button_click(self, event):
        self.notebook.close_tab(self)

    def on_button_enter(self, event):
        self.button.configure(image=CustomNotebookTab.active_close_image)

    def on_button_leave(self, event):
        self.button.configure(image=CustomNotebookTab.close_image)

    def update_state(self, active: bool) -> None:
        from thonny.ui_utils import ems_to_pixels

        if active:
            main_background = activeTabBackground
            # indicator_background = "systemTextBackgroundColor"
            # indicator_height = 1

            # indicator_background = border_color
            # indicator_height = 1

            indicator_background = active_indicator_color
            indicator_height = ems_to_pixels(0.2)
        else:
            main_background = frame_background
            indicator_background = border_color
            indicator_height = 1

        self.configure(background=main_background)
        self.label.configure(background=main_background)
        if self.button:
            self.button.configure(background=main_background)
        self.indicator.configure(background=indicator_background, height=indicator_height)


class CustomNotebookPage:
    def __init__(self, tab: CustomNotebookTab, content: tk.Widget):
        self.tab = tab
        self.content = content


class TextFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.text = tk.Text(self, highlightthickness=0, borderwidth=0, width=50, height=20)
        # self.text.grid_propagate(True)
        self.text.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(self, orient="vertical")
        self.scrollbar.grid(row=0, column=1, sticky="nsew")

        if sys.platform == "darwin":
            isdark = int(root.eval(f"tk::unsupported::MacWindowStyle isdark {root}"))
            # Not sure if it is good idea to use fixed colors, but no named (light-dark aware) color matches.
            # Best dynamic alternative is probably systemTextBackgroundColor
            if isdark:
                stripe_color = "#2d2e31"
                print("Dark")
            else:
                stripe_color = "#fafafa"
            stripe = tk.Frame(self, width=1, background=stripe_color)
            stripe.grid(row=0, column=1, sticky="nse")
            stripe.tkraise()

        self.scrollbar["command"] = self.text.yview
        self.text["yscrollcommand"] = self.scrollbar.set


if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes

        PROCESS_SYSTEM_DPI_AWARE = 1
        ctypes.OleDLL("shcore").SetProcessDpiAwareness(PROCESS_SYSTEM_DPI_AWARE)

    root = tk.Tk()
    root.geometry("800x600")

    style = ttk.Style()
    # style.theme_use("aqua")

    nb = CustomNotebook(root)

    for i in range(4):
        tf = TextFrame(nb)
        tf.text.insert("end", "print('hello world')\n" * i * 30)
        nb.add(tf, f"program{i}.py")

    nb.grid(sticky="nsew", row=0, column=0, padx=15, pady=15)
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    root.mainloop()
