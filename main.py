import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import requests

API_BASE = "https://api.acessorias.com"
RH_KEYWORDS = ("rh", "folha", "imposto")


def clean_identifier(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_rh_dept(name: str) -> bool:
    return any(kw in name.lower() for kw in RH_KEYWORDS)


def fetch_company(identifier: str, token: str):
    url = f"{API_BASE}/companies/{identifier}/?contacts&departments"
    res = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    res.raise_for_status()
    return res.json()


class App(tk.Tk):
    RED   = "#b91c1c"
    LIGHT = "#f0f2f5"
    WHITE = "#ffffff"
    ORANGE_BG = "#fff7ed"
    FONT  = ("Segoe UI", 10)
    FONT_BOLD = ("Segoe UI", 10, "bold")

    def __init__(self):
        super().__init__()
        self.title("Contatos RH — Acessórias")
        self.geometry("820x620")
        self.minsize(640, 480)
        self.configure(bg=self.LIGHT)
        self._build_ui()

    # ── Build UI ────────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel",  background=self.LIGHT, font=self.FONT)
        style.configure("TButton", font=self.FONT_BOLD, padding=6)
        style.configure("TEntry",  font=self.FONT, padding=4)
        style.configure("Red.TButton", foreground="white", background=self.RED,
                        font=self.FONT_BOLD)
        style.map("Red.TButton", background=[("active", "#991b1b")])
        style.configure("Treeview", font=self.FONT, rowheight=26)
        style.configure("Treeview.Heading", font=self.FONT_BOLD,
                        background="#f3f4f6", foreground="#444")
        style.map("Treeview", background=[("selected", "#fde68a")],
                  foreground=[("selected", "#000")])

        # ── Header
        hdr = tk.Frame(self, bg=self.RED, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Contatos RH por CNPJ", bg=self.RED, fg="white",
                 font=("Segoe UI", 14, "bold")).pack()
        tk.Label(hdr, text="Busca responsáveis de RH - Folha e RH - Impostos",
                 bg=self.RED, fg="#fca5a5", font=("Segoe UI", 9)).pack()

        # ── Form
        form = tk.Frame(self, bg=self.WHITE, padx=20, pady=16)
        form.pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(form, text="CNPJ / CPF", bg=self.WHITE,
                 font=self.FONT_BOLD).grid(row=0, column=0, sticky="w")
        tk.Label(form, text="Token da API", bg=self.WHITE,
                 font=self.FONT_BOLD).grid(row=0, column=1, sticky="w", padx=(16, 0))

        self.cnpj_var  = tk.StringVar()
        self.token_var = tk.StringVar()
        self.show_token = tk.BooleanVar(value=False)

        cnpj_entry = ttk.Entry(form, textvariable=self.cnpj_var, width=28)
        cnpj_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        cnpj_entry.bind("<Return>", lambda _: self._start_search())

        token_frame = tk.Frame(form, bg=self.WHITE)
        token_frame.grid(row=1, column=1, sticky="ew", padx=(16, 0), pady=(4, 0))
        self.token_entry = ttk.Entry(token_frame, textvariable=self.token_var,
                                     show="•", width=30)
        self.token_entry.pack(side="left", fill="x", expand=True)
        self.token_entry.bind("<Return>", lambda _: self._start_search())
        tk.Button(token_frame, text="👁", relief="flat", bg=self.WHITE, cursor="hand2",
                  command=self._toggle_token).pack(side="left", padx=(4, 0))

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(form, bg=self.WHITE)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.btn = ttk.Button(btn_frame, text="Buscar", style="Red.TButton",
                              command=self._start_search)
        self.btn.pack(side="left")
        self.status_lbl = tk.Label(btn_frame, text="", bg=self.WHITE,
                                   fg="#888", font=("Segoe UI", 9))
        self.status_lbl.pack(side="left", padx=10)

        # ── Notebook
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=20, pady=12)

        self.tab_rh       = self._make_tab(nb, "👥 RH - Folha & Impostos")
        self.tab_contatos = self._make_tab(nb, "📋 Contatos da Empresa")
        self.tab_deptos   = self._make_tab(nb, "🏢 Todos os Departamentos")

        nb.add(self.tab_rh,       text="👥 RH")
        nb.add(self.tab_contatos, text="📋 Contatos")
        nb.add(self.tab_deptos,   text="🏢 Departamentos")

        # Trees
        self.tree_rh = self._make_tree(
            self.tab_rh,
            ("Departamento", "Responsável", "E-mail"),
            (220, 180, 260),
        )
        self.tree_contatos = self._make_tree(
            self.tab_contatos,
            ("Nome", "E-mail", "Celular"),
            (200, 260, 160),
        )
        self.tree_deptos = self._make_tree(
            self.tab_deptos,
            ("ID", "Departamento", "Responsável", "E-mail"),
            (50, 200, 180, 240),
        )

        # Info labels
        self.info_rh = tk.Label(self.tab_rh, text="", bg=self.WHITE,
                                font=("Segoe UI", 9), fg="#888")
        self.info_rh.pack(side="bottom", anchor="w", padx=8, pady=4)

        # Copy hint
        for tab in (self.tab_rh, self.tab_contatos, self.tab_deptos):
            tk.Label(tab, text="Duplo clique em uma linha para copiar o e-mail",
                     bg=self.WHITE, fg="#aaa", font=("Segoe UI", 8)).pack(
                         side="bottom", anchor="e", padx=8)

        self.tree_rh.bind("<Double-1>",       lambda e: self._copy_email(self.tree_rh, 2))
        self.tree_contatos.bind("<Double-1>", lambda e: self._copy_email(self.tree_contatos, 1))
        self.tree_deptos.bind("<Double-1>",   lambda e: self._copy_email(self.tree_deptos, 3))

    def _make_tab(self, parent, text):
        f = tk.Frame(parent, bg=self.WHITE)
        return f

    def _make_tree(self, parent, cols, widths):
        frame = tk.Frame(parent, bg=self.WHITE)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, minwidth=60)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)
        return tree

    # ── Actions ─────────────────────────────────────────────────────────────

    def _toggle_token(self):
        self.show_token.set(not self.show_token.get())
        self.token_entry.config(show="" if self.show_token.get() else "•")

    def _copy_email(self, tree, col_index):
        sel = tree.selection()
        if not sel:
            return
        values = tree.item(sel[0], "values")
        if col_index < len(values) and values[col_index]:
            self.clipboard_clear()
            self.clipboard_append(values[col_index])
            self._set_status(f"E-mail copiado: {values[col_index]}")

    def _set_status(self, msg, color="#888"):
        self.status_lbl.config(text=msg, fg=color)

    def _start_search(self):
        cnpj  = self.cnpj_var.get().strip()
        token = self.token_var.get().strip()

        if not cnpj or not token:
            messagebox.showwarning("Atenção", "Preencha o CNPJ/CPF e o Token.")
            return

        self._clear_trees()
        self.btn.state(["disabled"])
        self._set_status("Buscando…")
        threading.Thread(target=self._search, args=(cnpj, token), daemon=True).start()

    def _search(self, cnpj, token):
        identifier = clean_identifier(cnpj)
        try:
            data = fetch_company(identifier, token)
            self.after(0, self._populate, data)
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            msgs = {401: "Token inválido (401).", 404: "CNPJ não encontrado (404).",
                    429: "Limite de requisições (429). Aguarde."}
            self.after(0, self._show_error, msgs.get(code, f"Erro HTTP {code}."))
        except requests.exceptions.ConnectionError:
            self.after(0, self._show_error, "Sem conexão com a API.")
        except requests.exceptions.Timeout:
            self.after(0, self._show_error, "Timeout — API demorou demais.")
        except Exception as exc:
            self.after(0, self._show_error, str(exc))
        finally:
            self.after(0, lambda: self.btn.state(["!disabled"]))

    def _show_error(self, msg):
        self._set_status(msg, color=self.RED)
        messagebox.showerror("Erro", msg)

    def _clear_trees(self):
        for tree in (self.tree_rh, self.tree_contatos, self.tree_deptos):
            tree.delete(*tree.get_children())
        self.info_rh.config(text="")

    def _populate(self, data: dict):
        deptos   = data.get("Departamentos") or []
        contatos = data.get("ContatosNaEmpresa") or []
        rh_deptos = [d for d in deptos if is_rh_dept(d.get("Nome", ""))]

        empresa = data.get("Razao", "")
        self._set_status(f"✔ {empresa}", color="#166534")

        # RH tab
        if rh_deptos:
            for d in rh_deptos:
                self.tree_rh.insert("", "end", tags=("rh",),
                    values=(d.get("Nome",""), d.get("RespNome","—"), d.get("RespEmail","—")))
            self.tree_rh.tag_configure("rh", background=self.ORANGE_BG)
            self.info_rh.config(
                text=f"{len(rh_deptos)} departamento(s) RH encontrado(s) em {empresa}")
        else:
            self.tree_rh.insert("", "end",
                values=("Nenhum departamento RH encontrado.", "", ""))
            self.info_rh.config(text="Sem departamentos RH nesta empresa.")

        # Contacts tab
        for c in contatos:
            self.tree_contatos.insert("", "end",
                values=(c.get("Nome",""), c.get("E-mail","—"), c.get("Celular","—")))

        # All departments tab
        for d in deptos:
            self.tree_deptos.insert("", "end",
                values=(d.get("ID",""), d.get("Nome",""),
                        d.get("RespNome","—"), d.get("RespEmail","—")))


if __name__ == "__main__":
    app = App()
    app.mainloop()
