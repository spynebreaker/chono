"""Main window: five big buttons in Spanish."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from . import APP_NAME, tools
from .search import Index, default_db

CONFIG = default_db().with_name("config.json")
FAMILY = "Segoe UI"  # replaced in App.__init__ by the first family installed


def pick_family(root: tk.Misc) -> str:
    from tkinter import font as tkfont

    have = set(tkfont.families(root))
    for f in ("Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans", "Liberation Sans"):
        if f in have:
            return f
    return "TkDefaultFont"


def F(size: int, bold: bool = False) -> tuple:
    return (FAMILY, size, "bold") if bold else (FAMILY, size)


def load_folder() -> Path:
    try:
        return Path(json.loads(CONFIG.read_text("utf-8"))["actas"])
    except Exception:
        default = Path.home() / "Documents" / "Actas"
        default.mkdir(parents=True, exist_ok=True)
        return default


def save_folder(p: Path) -> None:
    CONFIG.write_text(json.dumps({"actas": str(p)}), "utf-8")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        global FAMILY
        FAMILY = pick_family(self)
        self.title(APP_NAME)
        self.configure(bg="#f6f2ea")
        self.folder = load_folder()
        tk.Label(self, text=APP_NAME, font=F(26, True), bg="#f6f2ea").pack(pady=(24, 4))
        self.status = tk.Label(self, text="", font=F(14), bg="#f6f2ea", fg="#555")
        self.status.pack(pady=(0, 16))
        buttons = [
            ("Abrir un PDF", self.on_open),
            ("Leer acta escaneada", self.on_ocr),
            ("Buscar apellido", self.on_search),
            ("Unir actas", self.on_merge),
            ("Imprimir", self.on_print),
        ]
        for text, cmd in buttons:
            tk.Button(self, text=text, font=F(20), width=22, height=2, command=cmd,
                      bg="#ffffff", activebackground="#e8dcc6", relief="groove").pack(pady=8)
        tk.Button(self, text="Cambiar carpeta de actas", font=F(13),
                  command=self.on_folder, relief="flat", bg="#f6f2ea").pack(pady=(14, 24))
        self.show_folder()
        self.update_idletasks()  # size the window to its content (works with any screen scaling)
        self.minsize(self.winfo_reqwidth() + 80, self.winfo_reqheight())

    def show_folder(self) -> None:
        self.status.config(text=f"Carpeta de actas: {self.folder}")

    def pick_pdf(self, title: str, multiple: bool = False, images: bool = False):
        types = [("PDF", "*.pdf")]
        if images:
            types.append(("Imagen escaneada", "*.jpg *.jpeg *.png *.tif *.tiff"))
        ask = filedialog.askopenfilenames if multiple else filedialog.askopenfilename
        return ask(title=title, initialdir=self.folder, filetypes=types)

    def busy(self, message: str, work, done) -> None:
        self.status.config(text=message)
        self.config(cursor="watch")

        def run():
            try:
                result, error = work(), None
            except Exception as e:  # shown to the user in plain words
                result, error = None, e
            self.after(0, lambda: (self.config(cursor=""), self.show_folder(), done(result, error)))

        threading.Thread(target=run, daemon=True).start()

    # buttons
    def on_open(self) -> None:
        f = self.pick_pdf("Elija el PDF que quiere abrir")
        if f:
            tools.open_pdf(f)

    def on_ocr(self) -> None:
        f = self.pick_pdf("Elija el acta escaneada", images=True)
        if not f:
            return

        def done(out, err):
            if err:
                messagebox.showerror(APP_NAME, "No se pudo leer el acta. Pruebe con un escaneo más nítido.")
            else:
                messagebox.showinfo(APP_NAME, f"Listo. Se guardó como:\n{out.name}")
                tools.open_pdf(str(out))

        def progress(n, total):
            text = (f"Leyendo letra a mano: página {min(n + 1, total)} de {total}.\n"
                    "Tarda cerca de un minuto por página.")
            self.after(0, lambda: self.status.config(text=text))

        self.busy("Leyendo el acta, espere un momento...",
                  lambda: tools.read_scanned(f, progress=progress), done)

    def on_search(self) -> None:
        name = simpledialog.askstring(APP_NAME, "¿Qué apellido busca?", parent=self)
        if not name:
            return

        def work():
            idx = Index(default_db())
            try:
                stats = idx.update(self.folder)
                return idx.search(name), stats
            finally:
                idx.close()

        self.busy("Buscando en todas las actas...", work, lambda r, e: self.show_results(name, r, e))

    def show_results(self, name, result, err) -> None:
        if err:
            messagebox.showerror(APP_NAME, "No se pudo buscar en la carpeta de actas.")
            return
        hits, stats = result
        win = tk.Toplevel(self)
        win.title(f"Resultados: {name}")
        win.geometry("900x600")
        head = f"{len(hits)} resultados para \"{name}\""
        if stats["needs_ocr"]:
            head += f"   ({len(stats['needs_ocr'])} actas escaneadas sin leer todavía)"
        tk.Label(win, text=head, font=F(16, True)).pack(pady=8)
        lb = tk.Listbox(win, font=F(14), activestyle="none")
        lb.pack(fill="both", expand=True, padx=10, pady=6)
        for h in hits:
            lb.insert("end", f"{Path(h.path).name}  (pág. {h.page}, {h.match}):  {h.snippet}")
        tk.Label(win, text="Doble clic para abrir el acta", font=F(13)).pack(pady=6)
        lb.bind("<Double-Button-1>", lambda _e: lb.curselection() and tools.open_pdf(hits[lb.curselection()[0]].path))

    def on_merge(self) -> None:
        files = self.pick_pdf("Elija las actas que quiere unir (puede elegir varias)", multiple=True)
        if not files or len(files) < 2:
            if files:
                messagebox.showinfo(APP_NAME, "Elija por lo menos dos actas.")
            return
        out = filedialog.asksaveasfilename(title="Guardar las actas unidas como", initialdir=self.folder,
                                           defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                           initialfile="Familia.pdf")
        if not out:
            return

        def done(res, err):
            if err:
                messagebox.showerror(APP_NAME, "No se pudieron unir las actas.")
            else:
                tools.open_pdf(str(res))

        self.busy("Uniendo actas...", lambda: tools.merge(list(files), out), done)

    def on_print(self) -> None:
        f = self.pick_pdf("Elija el PDF que quiere imprimir")
        if f:
            tools.print_pdf(f)
            messagebox.showinfo(APP_NAME, "Enviado a la impresora.")

    def on_folder(self) -> None:
        d = filedialog.askdirectory(title="Carpeta donde guarda sus actas", initialdir=self.folder)
        if d:
            self.folder = Path(d)
            save_folder(self.folder)
            self.show_folder()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
