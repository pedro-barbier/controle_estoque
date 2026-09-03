import tkinter as tk
from tkinter import font as tkfont

from app import storage


class LoginDialog(tk.Toplevel):
    """Diálogo modal de login. Após fechar, `resultado` tem o nome do usuário
    autenticado (str) em caso de sucesso, ou None se foi cancelado."""

    def __init__(self, parent):
        super().__init__(parent)
        self.resultado = None

        self.title("Login")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)

        title_font = tkfont.Font(size=13, weight="bold")
        tk.Label(self, text="Informe usuário e senha", font=title_font).grid(
            row=0, column=0, columnspan=2, padx=20, pady=(20, 15)
        )

        tk.Label(self, text="Usuário:").grid(row=1, column=0, sticky="e", padx=(20, 5), pady=5)
        self.usuario_var = tk.StringVar()
        self.usuario_entry = tk.Entry(self, textvariable=self.usuario_var, width=25)
        self.usuario_entry.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=5)
        self.usuario_entry.bind("<Return>", self.on_submit)

        tk.Label(self, text="Senha:").grid(row=2, column=0, sticky="e", padx=(20, 5), pady=5)
        self.senha_var = tk.StringVar()
        self.senha_entry = tk.Entry(self, textvariable=self.senha_var, show="*", width=25)
        self.senha_entry.grid(row=2, column=1, sticky="w", padx=(0, 20), pady=5)
        self.senha_entry.bind("<Return>", self.on_submit)

        self.status_label = tk.Label(self, text="", fg="red")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=(5, 0))

        botoes = tk.Frame(self)
        botoes.grid(row=4, column=0, columnspan=2, pady=20)
        tk.Button(botoes, text="Entrar", width=10, command=self.on_submit).pack(side="left", padx=5)
        tk.Button(botoes, text="Cancelar", width=10, command=self.on_cancel).pack(side="left", padx=5)

        self.update_idletasks()
        largura, altura = self.winfo_reqwidth(), self.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - largura) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")

        self.transient(parent)
        self.grab_set()
        self.usuario_entry.focus_set()

    def on_submit(self, event=None):
        usuario = self.usuario_var.get().strip()
        senha = self.senha_var.get()
        if not usuario or not senha:
            self.status_label.config(text="Informe usuário e senha.")
            return "break"

        nome = storage.verificar_login(usuario, senha)
        if nome:
            self.resultado = nome
            self.destroy()
        else:
            self.status_label.config(text="Usuário ou senha inválidos.")
            self.senha_var.set("")
            self.senha_entry.focus_set()
        return "break"

    def on_cancel(self, event=None):
        self.resultado = None
        self.destroy()
