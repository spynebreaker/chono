"""Main window: five big buttons in Spanish; the other tools under "Más cosas"."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from . import APP_NAME, extras, tools
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


def load_config() -> dict:
    try:
        data = json.loads(CONFIG.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(data: dict) -> None:
    CONFIG.write_text(json.dumps(data, ensure_ascii=False), "utf-8")


def load_folder() -> Path:
    try:
        return Path(load_config()["actas"])
    except Exception:
        default = Path.home() / "Documents" / "Actas"
        default.mkdir(parents=True, exist_ok=True)
        return default


def save_folder(p: Path) -> None:
    data = load_config()
    data["actas"] = str(p)
    save_config(data)


def remember(key: str, value) -> None:
    data = load_config()
    data[key] = value
    save_config(data)


def big_button(parent, text: str, command, size: int = 20) -> tk.Button:
    return tk.Button(parent, text=text, font=F(size), width=24, height=2, command=command,
                     bg="#ffffff", activebackground="#e8dcc6", relief="groove")


def choose(parent, title: str, question: str, options: list[str]) -> int | None:
    """A small window with one big button per option. Returns the option's position."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg="#f6f2ea")
    win.transient(parent)
    tk.Label(win, text=question, font=F(16), bg="#f6f2ea", justify="center").pack(padx=24, pady=(20, 10))
    picked: list[int] = []
    for i, text in enumerate(options):
        big_button(win, text, lambda i=i: (picked.append(i), win.destroy()), 16).pack(padx=24, pady=6)
    tk.Button(win, text="Cancelar", font=F(13), relief="flat", bg="#f6f2ea", command=win.destroy).pack(pady=(6, 16))
    win.grab_set()
    parent.wait_window(win)
    return picked[0] if picked else None


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
            ("Escanear acta", self.on_scan),
            ("Buscar apellido", self.on_search),
            ("Más cosas", self.on_more),
        ]
        for text, cmd in buttons:
            big_button(self, text, cmd).pack(pady=8)
        tk.Button(self, text="Cambiar carpeta de actas", font=F(13),
                  command=self.on_folder, relief="flat", bg="#f6f2ea").pack(pady=(14, 24))
        self.show_folder()
        self.update_idletasks()  # size the window to its content (works with any screen scaling)
        self.minsize(self.winfo_reqwidth() + 80, self.winfo_reqheight())
        self.after(3000, self.auto_backup)

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
        if not f:
            return
        if tools.needs_form_reader(f):
            if tools.form_reader():
                other = messagebox.askyesno(
                    APP_NAME,
                    "Este formulario tiene un botón para revisarlo\n"
                    "que este programa todavía no puede usar.\n\n"
                    "¿Lo abro con el otro lector de formularios?\n"
                    "(Si elige No, se abre aquí y puede llenarlo e imprimirlo.)",
                )
                if other and tools.open_in_form_reader(f):
                    return
            else:
                messagebox.showinfo(
                    APP_NAME,
                    "Este formulario tiene un botón para revisarlo\n"
                    "que este programa todavía no puede usar.\n\n"
                    "Puede llenarlo e imprimirlo. Para revisarlo,\n"
                    "pida ayuda para instalar el lector de formularios.",
                )
        elif tools.government_form_signature(f):
            seen = load_config().get("signature_told", [])
            key = str(Path(f).resolve())
            if key not in seen:
                messagebox.showinfo(
                    APP_NAME,
                    "Este formulario del gobierno viene con un sello digital.\n\n"
                    "Arriba puede salir un aviso de que la firma no es válida.\n"
                    "Es normal: aparece al llenarlo. Puede ignorarlo,\n"
                    "el formulario sirve igual.",
                )
                remember("signature_told", (seen + [key])[-200:])
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

        def progress(stage, n, total):
            page = min(n + 1, total)
            if stage == "hand":
                text = (f"Leyendo letra a mano: página {page} de {total}.\n"
                        "Tarda cerca de un minuto por página.")
            else:
                text = f"Leyendo página {page} de {total}..."
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

    # Escanear acta
    def on_scan(self) -> None:
        how = choose(self, "Escanear acta", "¿Cómo quiere traer el acta?",
                     ["Con el escáner", "Con fotos del celular"])
        if how is None:
            return
        if how == 1:
            photos = filedialog.askopenfilenames(
                title="Elija las fotos de las páginas, en orden", initialdir=self.folder,
                filetypes=[("Fotos", "*.jpg *.jpeg *.png *.heic *.webp *.tif *.tiff")])
            if photos:
                self.make_record(list(photos))
            return
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="chono-escaneo-"))
        pages: list[str] = []
        while True:
            self.status.config(text=f"Escaneando la página {len(pages) + 1}...")
            self.update()
            try:
                got = tools.scan_page(tmp / f"pagina{len(pages) + 1}.jpg")
            except tools.NoScanner:
                self.show_folder()
                messagebox.showinfo(APP_NAME, "No encuentro el escáner.\n\n"
                                    "Revise que esté encendido y conectado,\n"
                                    "o use fotos del celular.")
                return
            self.show_folder()
            if got is None:
                break
            pages.append(str(got))
            if not messagebox.askyesno(APP_NAME, f"Lleva {len(pages)} página(s).\n\n¿Escanea otra página?"):
                break
        if pages:
            self.make_record(pages)

    def make_record(self, pictures: list[str]) -> None:
        import time

        name = self.folder / time.strftime("Escaneo %Y-%m-%d %H-%M.pdf")

        def work():
            pdf = tools.photos_to_pdf(pictures, name)
            out = tools.read_scanned(str(pdf))
            pdf.unlink()  # the copy with text replaces it
            final = name.with_name(name.stem + ".pdf")
            out.replace(final)
            return final

        def done(out, err):
            if err:
                messagebox.showerror(APP_NAME, "No se pudo leer el acta. Pruebe con fotos más nítidas.")
            else:
                messagebox.showinfo(APP_NAME, f"Listo. Se guardó en su carpeta de actas como:\n{out.name}")
                tools.open_pdf(str(out))

        self.busy(f"Leyendo {len(pictures)} página(s), espere un momento...", work, done)

    # Más cosas
    def on_more(self) -> None:
        win = tk.Toplevel(self)
        win.title("Más cosas")
        win.configure(bg="#f6f2ea")
        tk.Label(win, text="Más cosas", font=F(22, True), bg="#f6f2ea").pack(pady=(18, 10))
        items = [
            ("Ver y corregir el texto", self.on_review),
            ("Leer todas las actas", self.on_read_all),
            ("Achicar para enviar", self.on_smaller),
            ("Unir actas", self.on_merge),
            ("Imprimir", self.on_print),
            ("Copia de seguridad", self.on_backup),
        ]
        for text, cmd in items:
            big_button(win, text, lambda c=cmd: (win.destroy(), c()), 18).pack(padx=30, pady=6)
        tk.Button(win, text="Cerrar", font=F(13), relief="flat", bg="#f6f2ea", command=win.destroy).pack(pady=(8, 18))

    def on_review(self) -> None:
        f = self.pick_pdf("Elija el acta que quiere ver")
        if f:
            from .review import Review

            Review(self, Path(f))

    def on_read_all(self) -> None:
        self.status.config(text="Buscando actas sin leer...")
        self.update()
        files = extras.pending_scans(self.folder)
        self.show_folder()
        if not files:
            messagebox.showinfo(APP_NAME, "Todas las actas de su carpeta ya se pueden buscar.")
            return
        if not messagebox.askyesno(APP_NAME, f"Hay {len(files)} acta(s) escaneadas sin leer.\n\n"
                                   "¿Las leo todas ahora? Puede tardar un rato;\n"
                                   "puede seguir usando la computadora."):
            return

        def progress(n, total, name):
            text = f"Leyendo acta {min(n + 1, total)} de {total}: {name}" if name else "Terminando..."
            self.after(0, lambda: self.status.config(text=text))

        def done(res, err):
            if err:
                messagebox.showerror(APP_NAME, "No se pudieron leer las actas.")
                return
            made, failed = res
            text = f"Listo. Se leyeron {len(made)} acta(s)."
            if failed:
                text += f"\n\nNo se pudieron leer {len(failed)}:\n" + "\n".join(p.name for p in failed[:10])
            messagebox.showinfo(APP_NAME, text)

        self.busy("Leyendo actas...", lambda: extras.read_folder(files, progress), done)

    def on_smaller(self) -> None:
        f = self.pick_pdf("Elija el PDF que quiere enviar")
        if not f:
            return

        def done(out, err):
            if err:
                messagebox.showerror(APP_NAME, "No se pudo achicar este PDF.")
            elif out is None:
                messagebox.showinfo(APP_NAME, "Este PDF ya es liviano. Puede enviarlo así.")
            else:
                before, after = Path(f).stat().st_size, out.stat().st_size
                messagebox.showinfo(APP_NAME, f"Listo: pasó de {before / 1e6:.1f} MB a {after / 1e6:.1f} MB.\n\n"
                                    f"Se guardó al lado como:\n{out.name}")

        self.busy("Achicando el PDF...", lambda: extras.make_smaller(f), done)

    # Copia de seguridad
    def backup_extra(self) -> list[Path]:
        return [p for p in (default_db(), CONFIG) if p.exists()]

    def on_backup(self) -> None:
        dest = load_config().get("backup_to")
        if not dest or not Path(dest).exists():
            messagebox.showinfo(APP_NAME, "Elija dónde guardar la copia:\n"
                                "un disco o memoria USB conectado, o una carpeta en la nube.")
            dest = filedialog.askdirectory(title="Dónde guardar la copia de seguridad")
            if not dest:
                return
            remember("backup_to", dest)

        def done(res, err):
            if err:
                messagebox.showerror(APP_NAME, "No se pudo hacer la copia.\nRevise que el disco esté conectado.")
                return
            remember("backup_at", __import__("time").time())
            messagebox.showinfo(APP_NAME, f"Copia hecha. Archivos nuevos o cambiados: {res['copied']}.")

        self.busy("Haciendo la copia de seguridad...",
                  lambda: extras.backup(self.folder, dest, self.backup_extra()), done)

    def auto_backup(self) -> None:
        """Once a week, without asking, when the backup disk is connected."""
        cfg = load_config()
        dest = cfg.get("backup_to")
        if not dest or not extras.backup_due(cfg.get("backup_at")):
            return
        if not Path(dest).exists():
            self.status.config(text="Recuerde conectar el disco de la copia de seguridad.")
            return

        def work():
            res = extras.backup(self.folder, dest, self.backup_extra())
            remember("backup_at", __import__("time").time())
            return res

        def done(res, err):
            if not err:
                self.status.config(text="Copia de seguridad hecha.")
                self.after(8000, self.show_folder)

        threading.Thread(target=lambda: self.after(0, done, *self._run(work)), daemon=True).start()

    @staticmethod
    def _run(work):
        try:
            return work(), None
        except Exception as e:
            return None, e

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
