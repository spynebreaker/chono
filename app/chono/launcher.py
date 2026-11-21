"""Main window: five big cards in Spanish; the other tools under "Más cosas"."""

from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from . import APP_NAME, extras, more, tools, ui, update
from .search import Index, default_db

CONFIG = default_db().with_name("config.json")
def pick_family(root: tk.Misc) -> str:
    return ui.pick_family(root)


def F(size: int, bold: bool = False) -> tuple:
    return ui.F(size, bold)


def load_config() -> dict:
    try:
        data = json.loads(CONFIG.read_text("utf-8-sig"))
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


def big_button(parent, text: str, command, size: int = 20) -> tk.Canvas:
    return ui.Card(parent, text, "", command, icon="read", width=420, height=70, title_size=size - 2)


def choose(parent, title: str, question: str, options: list[str], icons: list[str] | None = None) -> int | None:
    """A small window with one big card per option. Returns the option's position."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=ui.BG)
    win.transient(parent)
    tk.Label(win, text=question, font=F(18, True), fg=ui.INK, bg=ui.BG, justify="center").pack(padx=28, pady=(22, 12))
    picked: list[int] = []
    for i, text in enumerate(options):
        icon = icons[i] if icons else "read"
        ui.Card(win, text, "", lambda i=i: (picked.append(i), win.destroy()), icon=icon,
                width=440, height=76, title_size=17).pack(padx=28, pady=6)
    ui.link(win, "Cancelar", win.destroy).pack(pady=(8, 18))
    win.grab_set()
    parent.wait_window(win)
    return picked[0] if picked else None


def ask_text(parent, title: str, question: str, secret: bool = False) -> str | None:
    """One question with a big text box. None when cancelled."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=ui.BG)
    win.transient(parent)
    tk.Label(win, text=question, font=F(17), fg=ui.INK, bg=ui.BG, justify="left", wraplength=560).pack(
        anchor="w", padx=28, pady=(22, 10))
    entry = tk.Entry(win, font=F(20), width=28, show="•" if secret else "", relief="solid", bd=1,
                     highlightthickness=2, highlightcolor=ui.ACCENT, highlightbackground=ui.BORDER)
    entry.pack(padx=28, pady=6, ipady=6)
    got: list[str] = []
    row = tk.Frame(win, bg=ui.BG)
    row.pack(fill="x", padx=20, pady=(12, 18))

    def ok(_e=None):
        got.append(entry.get())
        win.destroy()

    ui.Card(row, "Aceptar", "", ok, icon="open", width=220, height=64, title_size=16).pack(side="left", padx=8)
    ui.link(row, "Cancelar", win.destroy).pack(side="left", padx=8)
    entry.bind("<Return>", ok)
    entry.focus_set()
    win.grab_set()
    parent.wait_window(win)
    return got[0] if got else None


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        global FAMILY
        FAMILY = pick_family(self)
        self.title(APP_NAME)
        self.configure(bg=ui.BG)
        self.folder = load_folder()
        self.starting = sys.platform == "darwin"
        if self.starting:
            # Finder "Open With" / double click sends the files as an Apple event, right after
            # start. Then only the PDF opens (as on Windows): the window stays hidden and Chono
            # closes. Started from the Dock or Applications, the window appears.
            self.withdraw()
            self.createcommand("::tk::mac::OpenDocument", self.on_documents)
            self.createcommand("::tk::mac::ReopenApplication", self.show_window)
            self.after(STARTUP_WAIT_MS, self.show_window)
        ui.header(self, APP_NAME, "Sus actas y documentos, fáciles de leer y de encontrar")
        cards = tk.Frame(self, bg=ui.BG)
        cards.pack(anchor="w", padx=(24, 28), pady=(4, 0))
        main = [
            ("Abrir un PDF", "Ver, llenar formularios e imprimir", self.on_open, "open"),
            ("Leer acta escaneada", "Saca el texto, también de letra a mano", self.on_ocr, "read"),
            ("Escanear acta", "Con el escáner o con fotos del celular", self.on_scan, "scan"),
            ("Buscar una palabra", "Un nombre, apellido o lugar, en todas sus actas", self.on_search, "search"),
            ("Más cosas", "PDF, Word, clave, firma y más", self.on_more, "more"),
        ]
        for title, hint, cmd, icon in main:
            ui.Card(cards, title, hint, cmd, icon=icon).pack(pady=6)
        foot = tk.Frame(self, bg=ui.BG)
        foot.pack(fill="x", padx=(24, 28), pady=(12, 18))
        self.status = tk.Label(foot, text="", font=F(13), bg=ui.BG, fg=ui.MUTED, justify="left",
                               wraplength=520, anchor="w")
        self.status.pack(side="top", anchor="w", padx=6)
        ui.link(foot, "Cambiar carpeta de actas", self.on_folder, 13).pack(side="top", anchor="w")
        self.show_folder()
        self.update_idletasks()  # size the window to its content (works with any screen scaling)
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        self.after(3000, self.auto_backup)
        self.after(1500, self.check_update)

    def on_documents(self, *paths: str) -> None:
        pdfs = [p for p in paths if p.lower().endswith(".pdf")]
        for p in pdfs:
            open_checked(p)
        if self.starting and pdfs:
            self.starting = False
            self.after(200, self.destroy)

    def show_window(self) -> None:
        if self.starting:
            self.starting = False
        try:
            self.deiconify()
            self.lift()
        except tk.TclError:
            pass  # already closed after opening documents

    def check_update(self) -> None:
        """Once a day: a newer Chono on the internet is installed, and Chono opens again."""
        def work():
            config = load_config()
            version = update.check(config)
            save_config(config)
            if version:
                self.after(0, lambda: self.apply_update(version))

        threading.Thread(target=work, daemon=True).start()

    def apply_update(self, version: str) -> None:
        root = update.install_root()
        if root is None:
            return
        messagebox.showinfo(
            APP_NAME,
            "Hay una versión nueva de Chono.\n\n"
            "Se va a actualizar sola. Chono se cierra ahora y se vuelve a abrir en unos minutos.",
        )
        if update.start(root, version):
            self.destroy()

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
        open_checked(f)

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
        name = ask_text(self, "Buscar", "¿Qué palabra busca?\n(un nombre, un apellido, un lugar...)")
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
                     ["Con el escáner", "Con fotos del celular"], ["scan", "make"])
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
        win.configure(bg=ui.BG)
        win.transient(self)
        ui.header(win, "Más cosas", "Cada herramienta guarda una copia nueva al lado; el original no se toca.")
        groups = [
            ("Hacer y convertir", [
                ("Hacer PDF de un archivo", "Word, Excel, fotos...", self.on_make_pdf, "make"),
                ("Pasar a Word", "Para cambiar el texto", self.on_to_word, "word"),
                ("Unir actas", "Varios PDF en uno", self.on_merge, "merge"),
                ("Achicar para enviar", "Más liviano por correo", self.on_smaller, "shrink"),
            ]),
            ("Revisar y corregir", [
                ("Ver y corregir el texto", "Lo que leyó Chono", self.on_review, "eye"),
                ("Corregir texto impreso", "Cambiar una palabra", self.on_replace, "edit"),
                ("Comparar dos versiones", "Marca lo que cambió", self.on_compare, "compare"),
                ("Leer todas las actas", "Las que faltan", self.on_read_all, "stack"),
            ]),
            ("Proteger y firmar", [
                ("Poner o quitar clave", "Para abrir el PDF", self.on_password, "lock"),
                ("Tachar datos", "Se borran de verdad", self.on_black_out, "blackout"),
                ("Firmar", "Con su firma electrónica", self.on_sign, "sign"),
            ]),
            ("Imprimir y guardar", [
                ("Imprimir", "En su impresora", self.on_print, "print"),
                ("Copia de seguridad", "En un disco o la nube", self.on_backup, "backup"),
            ]),
        ]
        body = tk.Frame(win, bg=ui.BG)
        body.pack(padx=22, pady=(0, 4))
        row = 0
        for name, items in groups:
            ui.section(body, name).grid(row=row, column=0, columnspan=4, sticky="w", padx=6, pady=(10, 2))
            row += 1
            for i, (title, hint, cmd, icon) in enumerate(items):
                ui.Card(body, title, hint, lambda c=cmd: (win.destroy(), c()), icon=icon,
                        width=300, height=92, title_size=15).grid(row=row, column=i, padx=5, pady=4)
            row += 1
        ui.link(win, "Cerrar", win.destroy).pack(pady=(6, 16))

    def run_tool(self, message: str, work, ok_text, fail_text: str = "No se pudo hacer.") -> None:
        """Run a "Más cosas" tool in the background and say how it went."""
        def done(res, err):
            if isinstance(err, more.ChonoError):
                messagebox.showinfo(APP_NAME, str(err))
            elif err:
                messagebox.showerror(APP_NAME, fail_text)
            else:
                text, to_open = ok_text(res)
                messagebox.showinfo(APP_NAME, text)
                if to_open:
                    more.open_document(to_open)

        self.busy(message, work, done)

    def on_make_pdf(self) -> None:
        f = filedialog.askopenfilename(
            title="Elija el archivo que quiere pasar a PDF", initialdir=self.folder,
            filetypes=[("Documentos y fotos", " ".join(f"*{e}" for e in sorted(more.OFFICE_TYPES | more.IMAGE_TYPES))),
                       ("Todos", "*.*")])
        if f:
            self.run_tool("Haciendo el PDF...", lambda: more.make_pdf(f),
                          lambda out: (f"Listo. Se guardó al lado como:\n{out.name}", out),
                          "No se pudo hacer el PDF de ese archivo.")

    def on_to_word(self) -> None:
        f = self.pick_pdf("Elija el PDF que quiere pasar a Word")
        if f:
            self.run_tool("Pasando a Word...", lambda: more.to_word(f),
                          lambda out: (f"Listo. Se guardó al lado como:\n{out.name}", out),
                          "No se pudo pasar este PDF a Word.")

    def on_password(self) -> None:
        f = self.pick_pdf("Elija el PDF")
        if not f:
            return
        if more.is_protected(f):
            pw = ask_text(self, "Quitar clave", "Este PDF tiene clave.\nEscriba la clave para quitársela:", secret=True)
            if pw is not None:
                self.run_tool("Quitando la clave...", lambda: more.remove_password(f, pw),
                              lambda out: (f"Listo. La copia sin clave se llama:\n{out.name}", None))
            return
        pw = ask_text(self, "Poner clave", "Escriba la clave que tendrá el PDF.\nAnótela: sin ella no se puede abrir.",
                      secret=True)
        if not pw:
            return
        again = ask_text(self, "Poner clave", "Escriba la clave otra vez:", secret=True)
        if again != pw:
            if again is not None:
                messagebox.showinfo(APP_NAME, "Las dos claves no son iguales. Pruebe otra vez.")
            return
        self.run_tool("Poniendo la clave...", lambda: more.add_password(f, pw),
                      lambda out: (f"Listo. La copia con clave se llama:\n{out.name}", None))

    def on_black_out(self) -> None:
        f = self.pick_pdf("Elija el PDF donde quiere tachar algo")
        if not f:
            return
        words = ask_text(self, "Tachar datos", "¿Qué quiere tachar?\n"
                         "Escriba el nombre, número o palabra. Si son varios, sepárelos con punto y coma (;).")
        if words:
            self.run_tool("Tachando...", lambda: more.black_out(f, words.split(";")),
                          lambda r: (f"Listo. Se tachó en {r[1]} lugar(es).\nSe guardó al lado como:\n{r[0].name}", r[0]))

    def on_compare(self) -> None:
        old = self.pick_pdf("Elija la versión ANTERIOR")
        if not old:
            return
        new = self.pick_pdf("Ahora elija la versión NUEVA")
        if not new:
            return

        def said(r):
            out, n = r
            if n == 0:
                return "Las dos versiones dicen lo mismo.", None
            return (f"Hay {n} cambio(s). Están marcados en amarillo en la versión nueva;\n"
                    f"lo que se quitó aparece en una notita.\n\nSe guardó como:\n{out.name}", out)

        self.run_tool("Comparando...", lambda: more.compare(old, new), said)

    def on_sign(self) -> None:
        f = self.pick_pdf("Elija el PDF que quiere firmar")
        if not f:
            return
        cert = load_config().get("signature_file")
        if not cert or not Path(cert).exists():
            messagebox.showinfo(APP_NAME, "Elija el archivo de su firma electrónica\n"
                                "(termina en .p12 o .pfx). Se lo pide una sola vez.")
            cert = filedialog.askopenfilename(title="Archivo de su firma electrónica",
                                              filetypes=[("Firma electrónica", "*.p12 *.pfx")])
            if not cert:
                return
            remember("signature_file", cert)
        pw = ask_text(self, "Firmar", "Escriba la clave de su firma electrónica:", secret=True)
        if pw is None:
            return
        self.run_tool("Firmando...", lambda: more.sign(f, cert, pw),
                      lambda out: (f"Listo. La copia firmada se llama:\n{out.name}", out))

    def on_replace(self) -> None:
        f = self.pick_pdf("Elija el PDF que quiere corregir")
        if not f:
            return
        old = ask_text(self, "Corregir texto", "¿Qué texto quiere cambiar?\n(escríbalo tal como aparece)")
        if not old:
            return
        new = ask_text(self, "Corregir texto", f"¿Qué debe decir en lugar de «{old}»?")
        if new is None:
            return
        self.run_tool("Corrigiendo...", lambda: more.replace_text(f, old, new),
                      lambda r: (f"Listo. Se cambió en {r[1]} lugar(es).\nSe guardó al lado como:\n{r[0].name}", r[0]))

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


def open_checked(f: str, watch: bool = False) -> None:
    """Open a PDF the way the Open button does: say first what a form needs, then open it."""
    if tools.needs_form_reader(f):
        if tools.form_reader():
            other = messagebox.askyesno(
                APP_NAME,
                "Este formulario tiene botones o casillas automáticas\n"
                "que este programa todavía no puede usar.\n\n"
                "¿Lo abro con el otro lector de formularios?\n"
                "(Si elige No, se abre aquí y puede llenarlo e imprimirlo.)",
            )
            if other and tools.open_in_form_reader(f):
                return
        else:
            messagebox.showinfo(
                APP_NAME,
                "Este formulario tiene botones o casillas automáticas\n"
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
                "el formulario sirve igual.\n\n"
                "Llénelo completo antes de mandarlo:\n"
                "quien lo reciba lo puede ver e imprimir,\n"
                "pero quizá no pueda escribir más en él.",
            )
            remember("signature_told", (seen + [key])[-200:])
    if not tools.open_pdf(f, watch=watch):
        messagebox.showinfo(
            APP_NAME,
            "El programa de PDF no respondió.\n\nEspere un momento y vuelva a abrir el archivo.",
        )


STARTUP_WAIT_MS = 900  # how long a Mac start waits for Finder's documents before showing the window


def main(argv: list[str] | None = None) -> None:
    """Start Chono; with a PDF path (Open with, right click), just open that PDF."""
    args = sys.argv[1:] if argv is None else argv
    pdfs = [a for a in args if a.lower().endswith(".pdf") and Path(a).is_file()]
    if pdfs:
        root = tk.Tk()
        root.withdraw()
        for f in pdfs:
            open_checked(f, watch=True)
        root.destroy()
        return
    App().mainloop()


if __name__ == "__main__":
    main()
