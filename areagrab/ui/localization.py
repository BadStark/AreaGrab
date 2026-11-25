"""Tk helpers for application-language text and modal buttons."""
from tkinter import simpledialog, ttk

from ..i18n import MESSAGE_KEYS


def capture_labels(parent):
    """Keep source labels so a second language change can translate them again."""
    labels = {}
    for child in parent.winfo_children():
        if "text" in child.keys() and child.cget("text") in MESSAGE_KEYS:
            labels[child] = child.cget("text")
        labels.update(capture_labels(child))
    return labels


def update_labels(labels, translate):
    for widget, source in labels.items():
        widget.configure(text=translate(source))


class LocalizedDialog(simpledialog.Dialog):
    def __init__(self, parent, title, message, translate, choices=("ОК",)):
        self.message = message
        self.translate = translate
        self.choices = choices
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text=self.message, wraplength=440, justify="left").pack(
            padx=18, pady=12
        )

    def buttonbox(self):
        box = ttk.Frame(self, padding=(12, 0, 12, 12))
        default = len(self.choices) - 1
        for index, label in enumerate(self.choices):
            ttk.Button(
                box, text=self.translate(label),
                default="active" if index == default else "normal",
                command=lambda choice=index: self.choose(choice),
            ).pack(side="left", padx=4)
        box.pack()
        self.bind("<Return>", lambda _event: self.choose(default))
        self.bind("<Escape>", self.cancel)

    def choose(self, index):
        self.result = index
        self.cancel()
