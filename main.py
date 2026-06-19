import json
import re
import threading
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox

API_BASE = "https://api.acessorias.com"
RH_KEYWORDS = ("rh", "folha", "imposto")


def clean_identifier(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_rh_dept(name: str) -> bool:
    return any(kw in name.lower() for kw in RH_KEYWORDS)


def fetch_company(identifier: str, token: str) -> dict:
    url = f"{API_BASE}/companies/{identifier}/?contacts&departments"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


class App(tk.Tk):
    RED       = "#b91c1c"
    LIGHT     = "#f0f2f5"
    WHITE     = "#ffffff"
    ORANGE_BG = "#fff7ed"

    def __init__(self):
        super().__init__()
        self.title("Contatos RH — Acessórias")
        self.geometry("860x580")
        self.minsize(660, 440)
        self.configure(bg=self.LIGHT)
        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel",  background=self.LIGHT, font=("Segoe UI", 10))
        style.configure("TEntry",  font=("Segoe UI", 10), padding=4)
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        style.configure("Treeview.Heading",
                        font=("Segoe UI", 10, "bold"),
                        background="#f3f4f6", foreground="#444")
        style.map("Treeview",
                  background=[("selected", "#fde68a")],
                  foreground=[("selected", "#000")])

        # Header
        hdr = tk.Frame(self, bg=self.RED, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Contatos RH por CNPJ",
                 bg=self.RED, fg="white",
                 font=("Segoe UI", 14, "bold")).pack()
        tk.Label(hdr, text="Responsáveis por RH - Folha e RH - Impostos",
                 bg=self.RED, fg="#fca5a5",
                 font=("Segoe UI", 9)).pack()

        # Form
        form = tk.Frame(self, bg=self.WHITE, padx=20, pady=14)
        form.pack(fill="x", padx=20, pady=(14, 0))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        tk.Label(form, text="CNPJ / CPF", bg=self.WHITE,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(form, text="Token da API", bg=self.WHITE,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=(14, 0))

        self.cnpj_var  = tk.StringVar()
        self.token_var = tk.StringVar()

        cnpj_e = ttk.Entry(form, textvariable=self.cnpj_var, width=28)
        cnpj_e.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        cnpj_e.bind("<Return>", lambda _: self._start_search())

        tok_frame = tk.Frame(form, bg=self.WHITE)
        tok_frame.grid(row=1, column=1, sticky="ew", padx=(14, 0), pady=(3, 0))

        self._tok_entry = ttk.Entry(tok_frame, textvariable=self.token_var, show="•", width=32)
        self._tok_entry.pack(side="left", fill="x", expand=True)
        self._tok_entry.bind("<Return>", lambda _: self._start_search())

        tk.Button(tok_frame, text="👁", relief="flat", bg=self.WHITE,
                  cursor="hand2", font=("Segoe UI", 11),
                  command=self._toggle_token).pack(side="left", padx=(4, 0))

        btn_row = tk.Frame(form, bg=self.WHITE)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self._btn = tk.Button(btn_row, text="  Buscar  ",
                              bg=self.RED, fg="white", relief="flat",
                              font=("Segoe UI", 10, "bold"), cursor="hand2",
                              activebackground="#991b1b", activeforeground="white",
                              command=self._start_search)
        self._btn.pack(side="left")

        self._status = tk.Label(btn_row, text="", bg=self.WHITE,
                                fg="#888", font=("Segoe UI", 9))
        self._status.pack(side="left", padx=10)

        # Notebook
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=20, pady=10)

        self._tree_rh       = self._make_tab(nb, "👥 RH",
            ("Departamento", "Responsável", "E-mail"), (220, 180, 280))
        self._tree_contatos = self._make_tab(nb, "📋 Contatos",
            ("Nome", "E-mail", "Celular"), (200, 270, 150))
        self._tree_deptos   = self._make_tab(nb, "🏢 Departamentos",
            ("ID", "Departamento", "Responsável", "E-mail"), (45, 200, 180, 240))

        hint = "Duplo clique → copia o e-mail"
        self._tree_rh.bind("<Double-1>",
                           lambda _: self._copy_col(self._tree_rh, 2))
        self._tree_contatos.bind("<Double-1>",
                                 lambda _: self._copy_col(self._tree_contatos, 1))
        self._tree_deptos.bind("<Double-1>",
                               lambda _: self._copy_col(self._tree_deptos, 3))

        tk.Label(self, text=hint, bg=self.LIGHT, fg="#aaa",
                 font=("Segoe UI", 8)).pack(anchor="e", padx=22, pady=(0, 6))

    def _make_tab(self, nb, label, cols, widths):
        frame = tk.Frame(nb, bg=self.WHITE)
        nb.add(frame, text=label)

        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, minwidth=50)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=6, pady=6)
        return tree

    # ── Actions ─────────────────────────────────────────────────────────────

    def _toggle_token(self):
        self._tok_entry.config(
            show="" if self._tok_entry.cget("show") == "•" else "•"
        )

    def _copy_col(self, tree, col):
        sel = tree.selection()
        if not sel:
            return
        val = tree.item(sel[0], "values")
        if col < len(val) and val[col] and val[col] != "—":
            self.clipboard_clear()
            self.clipboard_append(val[col])
            self._set_status(f"Copiado: {val[col]}", "#166534")

    def _set_status(self, msg, color="#888"):
        self._status.config(text=msg, fg=color)

    def _clear(self):
        for t in (self._tree_rh, self._tree_contatos, self._tree_deptos):
            t.delete(*t.get_children())

    def _start_search(self):
        cnpj  = self.cnpj_var.get().strip()
        token = self.token_var.get().strip()
        if not cnpj or not token:
            messagebox.showwarning("Atenção", "Preencha o CNPJ/CPF e o Token.")
            return
        self._clear()
        self._btn.config(state="disabled")
        self._set_status("Buscando…")
        threading.Thread(target=self._run, args=(cnpj, token), daemon=True).start()

    def _run(self, cnpj, token):
        try:
            data = fetch_company(clean_identifier(cnpj), token)
            self.after(0, self._populate, data)
        except urllib.error.HTTPError as e:
            msgs = {401: "Token inválido (401).",
                    404: "CNPJ não encontrado (404).",
                    429: "Limite de requisições (429). Aguarde.",
                    204: "Sem conteúdo para este CNPJ (204)."}
            self.after(0, self._error, msgs.get(e.code, f"Erro HTTP {e.code}."))
        except urllib.error.URLError as e:
            self.after(0, self._error, f"Sem conexão: {e.reason}")
        except TimeoutError:
            self.after(0, self._error, "Timeout — API demorou demais.")
        except Exception as e:
            self.after(0, self._error, str(e))
        finally:
            self.after(0, lambda: self._btn.config(state="normal"))

    def _error(self, msg):
        self._set_status(msg, self.RED)
        messagebox.showerror("Erro", msg)

    def _populate(self, data: dict):
        deptos   = data.get("Departamentos") or []
        contatos = data.get("ContatosNaEmpresa") or []
        rh       = [d for d in deptos if is_rh_dept(d.get("Nome", ""))]

        self._set_status(f"✔  {data.get('Razao', '')}", "#166534")

        # Aba RH
        if rh:
            for d in rh:
                self._tree_rh.insert("", "end", tags=("rh",), values=(
                    d.get("Nome", ""),
                    d.get("RespNome") or "—",
                    d.get("RespEmail") or "—",
                ))
            self._tree_rh.tag_configure("rh", background=self.ORANGE_BG)
        else:
            self._tree_rh.insert("", "end",
                                 values=("Nenhum departamento RH encontrado.", "", ""))

        # Aba Contatos
        for c in contatos:
            self._tree_contatos.insert("", "end", values=(
                c.get("Nome", ""),
                c.get("E-mail") or "—",
                c.get("Celular") or "—",
            ))

        # Aba Todos os Departamentos
        for d in deptos:
            self._tree_deptos.insert("", "end", values=(
                d.get("ID", ""),
                d.get("Nome", ""),
                d.get("RespNome") or "—",
                d.get("RespEmail") or "—",
            ))


if __name__ == "__main__":
    App().mainloop()
