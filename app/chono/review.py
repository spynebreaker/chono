"""Window to look at a record and its text side by side: correct the text,
highlight, add a note, read aloud, and pass it to Word."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import pypdfium2 as pdfium

from . import APP_NAME, extras, tools
from .ui import BG


def _font(size: int, bold: bool = False) -> tuple:
    from . import launcher

    return launcher.F(size, bold)


class Review(tk.Toplevel):
    def __init__(self, parent: tk.Misc, pdf: Path) -> None:
        super().__init__(parent)
        self.pdf = pdf
        self.page = 1
        self.voice = None
        self.marking = False
        self.drag = None
        self.title(pdf.name)
        self.configure(bg=BG)
        self.geometry("1400x900")
        self.protocol("WM_DELETE_WINDOW", self.close)

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=10, pady=8)
        b = dict(font=_font(15), bg="#ffffff", activebackground="#e8dcc6", relief="groove", padx=10)
        tk.Button(top, text="< Página anterior", command=lambda: self.go(-1), **b).pack(side="left")
        self.where = tk.Label(top, text="", font=_font(16, True), bg=BG)
        self.where.pack(side="left", padx=14)
        tk.Button(top, text="Página siguiente >", command=lambda: self.go(1), **b).pack(side="left")
        tk.Button(top, text="Pasar a Word", command=self.to_word, **b).pack(side="right")

        body = tk.PanedWindow(self, orient="horizontal", sashwidth=8, bg=BG)
        body.pack(fill="both", expand=True, padx=10)
        self.canvas = tk.Canvas(body, bg="#dddddd", highlightthickness=0, cursor="arrow")
        body.add(self.canvas, minsize=400, width=680)
        right = tk.Frame(body, bg=BG)
        body.add(right, minsize=400)
        tk.Label(right, text="Texto de la página (puede corregirlo)", font=_font(14), bg=BG).pack(anchor="w")
        self.text = tk.Text(right, font=_font(16), wrap="word", undo=True, padx=10, pady=10)
        self.text.pack(fill="both", expand=True)
        self.notes = tk.Label(right, text="", font=_font(13), bg=BG, fg="#5a4a2a", justify="left", wraplength=600)
        self.notes.pack(anchor="w", pady=4)

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=10, pady=10)
        tk.Button(bottom, text="Guardar texto corregido", command=self.save_text, **b).pack(side="left", padx=4)
        self.read_btn = tk.Button(bottom, text="Leer en voz alta", command=self.read_aloud, **b)
        self.read_btn.pack(side="left", padx=4)
        self.mark_btn = tk.Button(bottom, text="Resaltar", command=self.toggle_mark, **b)
        self.mark_btn.pack(side="left", padx=4)
        tk.Button(bottom, text="Agregar nota", command=self.add_note, **b).pack(side="left", padx=4)
        self.hint = tk.Label(bottom, text="", font=_font(13), bg=BG, fg="#555")
        self.hint.pack(side="left", padx=12)

        self.canvas.bind("<Configure>", lambda _e: self.draw_page())
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.motion)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        doc = pdfium.PdfDocument(str(pdf))
        self.count = len(doc)
        doc.close()
        self.show()

    # pages
    def go(self, step: int) -> None:
        if self.text.edit_modified() and messagebox.askyesno(APP_NAME, "¿Guardo el texto corregido de esta página?", parent=self):
            self.save_text()
        self.page = min(max(1, self.page + step), self.count)
        self.show()

    def show(self) -> None:
        self.where.config(text=f"Página {self.page} de {self.count}")
        texts = extras.page_texts(self.pdf)
        self.text.delete("1.0", "end")
        self.text.insert("1.0", texts[self.page - 1] if self.page <= len(texts) else "")
        self.text.edit_modified(False)
        try:
            on_page = extras.notes(self.pdf).get(self.page, [])
        except Exception:
            on_page = []
        self.notes.config(text="Notas: " + " | ".join(on_page) if on_page else "")
        self.draw_page()

    def draw_page(self) -> None:
        from PIL import ImageTk

        w, h = max(self.canvas.winfo_width(), 50), max(self.canvas.winfo_height(), 50)
        doc = pdfium.PdfDocument(str(self.pdf))
        try:
            pg = doc[self.page - 1]
            pw, ph = pg.get_size()
            self.scale = min(w / pw, h / ph)
            img = pg.render(scale=self.scale, may_draw_forms=True).to_pil()
            self.page_h = ph
        finally:
            doc.close()
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.ox, self.oy = (w - img.width) // 2, (h - img.height) // 2
        self.canvas.create_image(self.ox, self.oy, image=self.photo, anchor="nw")

    # text
    def save_text(self) -> None:
        extras.save_correction(self.pdf, self.page, self.text.get("1.0", "end-1c"))
        self.text.edit_modified(False)
        self.hint.config(text="Texto guardado. La búsqueda ya lo usa.")

    def to_word(self) -> None:
        out = filedialog.asksaveasfilename(parent=self, title="Guardar el texto en Word como",
                                           initialdir=self.pdf.parent, initialfile=self.pdf.stem + ".docx",
                                           defaultextension=".docx", filetypes=[("Word", "*.docx")])
        if out:
            extras.export_transcription(self.pdf, out)
            tools.open_file(out)

    # voice
    def read_aloud(self) -> None:
        if self.voice is not None and self.voice.poll() is None:
            tools.stop_speaking(self.voice)
            self.voice = None
            self.read_btn.config(text="Leer en voz alta")
            return
        try:
            text = self.text.get("sel.first", "sel.last")
        except tk.TclError:
            text = self.text.get("1.0", "end-1c")
        self.voice = tools.speak(text)
        if self.voice is None:
            messagebox.showinfo(APP_NAME, "Esta computadora no tiene voz instalada.", parent=self)
            return
        self.read_btn.config(text="Parar la lectura")
        self.after(500, self.watch_voice)

    def watch_voice(self) -> None:
        if self.voice is not None and self.voice.poll() is None:
            self.after(500, self.watch_voice)
        else:
            if self.voice is not None and self.voice.returncode == tools.NO_SPANISH_VOICE:
                messagebox.showinfo(APP_NAME, "Esta computadora no tiene voz en español.\n"
                                    "Se agrega en Configuración > Hora e idioma > Voz.", parent=self)
            self.voice = None
            self.read_btn.config(text="Leer en voz alta")

    # highlight and notes
    def toggle_mark(self) -> None:
        self.marking = not self.marking
        self.mark_btn.config(relief="sunken" if self.marking else "groove")
        self.canvas.config(cursor="crosshair" if self.marking else "arrow")
        self.hint.config(text="Pase el ratón sobre lo que quiere resaltar, con el botón apretado." if self.marking else "")

    def press(self, e) -> None:
        if self.marking:
            self.drag = (e.x, e.y)
            self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="#d4a000", width=2)

    def motion(self, e) -> None:
        if self.drag:
            self.canvas.coords(self.rect, self.drag[0], self.drag[1], e.x, e.y)

    def release(self, e) -> None:
        if not self.drag:
            return
        (x0, y0), self.drag = self.drag, None

        def to_pdf(x, y):
            return (x - self.ox) / self.scale, self.page_h - (y - self.oy) / self.scale

        a, b = to_pdf(x0, y0), to_pdf(e.x, e.y)
        if self.change(lambda: extras.add_highlight(self.pdf, self.page, (a[0], a[1], b[0], b[1]))):
            self.draw_page()

    def add_note(self) -> None:
        text = simpledialog.askstring(APP_NAME, "Escriba la nota para esta página:", parent=self)
        if text and self.change(lambda: extras.add_note(self.pdf, self.page, text)):
            self.show()

    def change(self, action) -> bool:
        try:
            action()
            return True
        except extras.CannotMark:
            messagebox.showinfo(APP_NAME, "Este documento es un formulario o tiene firma.\n"
                                "No se le pueden poner marcas aquí, para no dañarlo.", parent=self)
        except PermissionError:
            messagebox.showinfo(APP_NAME, "El PDF está abierto en otro programa.\n"
                                "Ciérrelo y pruebe otra vez.", parent=self)
        except Exception:
            messagebox.showerror(APP_NAME, "No se pudo guardar la marca.", parent=self)
        self.draw_page()
        return False

    def close(self) -> None:
        tools.stop_speaking(self.voice)
        if self.text.edit_modified() and messagebox.askyesno(APP_NAME, "¿Guardo el texto corregido de esta página?", parent=self):
            self.save_text()
        self.destroy()
