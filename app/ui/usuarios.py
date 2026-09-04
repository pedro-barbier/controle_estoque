import tkinter as tk
from tkinter import messagebox, ttk

from app import storage


class UsuariosFrame(tk.Frame):
    """Tela de administração de usuários — só acessível a administradores
    (ver PROTECTED_FRAMES/ADMIN_FRAMES em main.py)."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.editando_usuario = None

        tk.Label(self, text="Administradores", font=("TkDefaultFont", 16, "bold")).pack(pady=15)

        form = tk.Frame(self)
        form.pack(pady=10)

        tk.Label(form, text="Nome de usuário:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.usuario_var = tk.StringVar()
        self.usuario_entry = tk.Entry(form, textvariable=self.usuario_var, width=32)
        self.usuario_entry.grid(row=0, column=1, pady=5)
        self.usuario_entry.bind("<Return>", self.on_submit)

        self.senha_label = tk.Label(form, text="Senha:")
        self.senha_label.grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.senha_var = tk.StringVar()
        self.senha_entry = tk.Entry(form, textvariable=self.senha_var, show="*", width=32)
        self.senha_entry.grid(row=1, column=1, pady=5)
        self.senha_entry.bind("<Return>", self.on_submit)

        self.admin_var = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text="Administrador", variable=self.admin_var).grid(
            row=2, column=0, columnspan=2, pady=(0, 5)
        )

        botoes_form = tk.Frame(form)
        botoes_form.grid(row=3, column=0, columnspan=2, pady=12)
        self.submit_button = tk.Button(botoes_form, text="Adicionar Usuário", command=self.on_submit)
        self.submit_button.pack(side="left", padx=5)
        self.cancelar_button = tk.Button(botoes_form, text="Cancelar Edição", command=self.on_cancelar_edicao)

        self.status_label = tk.Label(self, text="", fg="red")
        self.status_label.pack()

        columns = ("usuario", "admin")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("usuario", text="Usuário")
        self.tree.heading("admin", text="Administrador")
        self.tree.column("usuario", width=300)
        self.tree.column("admin", width=140, anchor="center")
        self.tree.pack(pady=10, fill="both", expand=True, padx=20)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_tree)

        acoes = tk.Frame(self)
        acoes.pack(pady=5)
        tk.Button(acoes, text="Editar Selecionado", command=self.on_editar).pack(side="left", padx=5)
        tk.Button(acoes, text="Remover Selecionado", command=self.on_remove).pack(side="left", padx=5)

        tk.Button(self, text="Voltar ao Menu", command=self.on_back_to_menu).pack(side="bottom", pady=15)

    def on_show(self):
        self._resetar_form()
        self.refresh_tree()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        usuarios = sorted(storage.listar_usuarios(), key=lambda u: u["usuario"].lower())
        for u in usuarios:
            self.tree.insert("", "end", iid=u["usuario"], values=(u["usuario"], "Sim" if u["admin"] else "Não"))

    def _resetar_form(self):
        self.editando_usuario = None
        self.usuario_var.set("")
        self.senha_var.set("")
        self.admin_var.set(False)
        self.senha_label.config(text="Senha:")
        self.submit_button.config(text="Adicionar Usuário")
        self.cancelar_button.pack_forget()
        self.status_label.config(text="", fg="red")
        self.usuario_entry.focus_set()

    def on_select_tree(self, event=None):
        selecionado = self.tree.selection()
        if not selecionado:
            return
        self._carregar_para_edicao(selecionado[0])

    def on_editar(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um usuário da lista para editar.")
            return
        self._carregar_para_edicao(selecionado[0])

    def _carregar_para_edicao(self, usuario):
        dados = next((u for u in storage.listar_usuarios() if u["usuario"] == usuario), None)
        if not dados:
            return
        self.editando_usuario = dados["usuario"]
        self.usuario_var.set(dados["usuario"])
        self.senha_var.set("")
        self.admin_var.set(bool(dados["admin"]))
        self.senha_label.config(text="Senha (deixe em branco para manter):")
        self.submit_button.config(text="Salvar Alterações")
        self.cancelar_button.pack(side="left", padx=5)
        self.status_label.config(text="", fg="red")
        self.usuario_entry.focus_set()

    def on_cancelar_edicao(self):
        self._resetar_form()

    def on_submit(self, event=None):
        usuario = self.usuario_var.get().strip()
        senha = self.senha_var.get()
        admin = self.admin_var.get()

        if not usuario:
            self.status_label.config(text="Informe o nome de usuário.", fg="red")
            return "break"

        try:
            if self.editando_usuario:
                storage.atualizar_usuario(
                    self.editando_usuario, novo_usuario=usuario, nova_senha=senha or None, admin=admin
                )
                mensagem = f"Usuário '{usuario}' atualizado."
            else:
                if not senha:
                    self.status_label.config(text="Informe a senha.", fg="red")
                    return "break"
                storage.criar_usuario(usuario, senha, admin=admin)
                mensagem = f"Usuário '{usuario}' adicionado."
        except ValueError as exc:
            self.status_label.config(text=str(exc), fg="red")
            return "break"

        self._resetar_form()
        self.status_label.config(text=mensagem, fg="green")
        self.refresh_tree()
        return "break"

    def try_advance(self):
        self.on_submit()

    def on_remove(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um usuário da lista para remover.")
            return
        usuario = selecionado[0]
        if usuario.strip().lower() == (self.controller.usuario_logado or "").strip().lower():
            messagebox.showerror("Ação não permitida", "Você não pode remover o usuário com o qual está logado.")
            return
        if not messagebox.askyesno("Confirmar", f"Remover o usuário '{usuario}'?"):
            return
        try:
            storage.remover_usuario(usuario)
        except ValueError as exc:
            messagebox.showerror("Ação não permitida", str(exc))
            return
        self._resetar_form()
        self.status_label.config(text=f"Usuário '{usuario}' removido.", fg="green")
        self.refresh_tree()

    def on_back_to_menu(self):
        self.controller.show_frame("MainMenu")
