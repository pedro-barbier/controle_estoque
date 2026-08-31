import tkinter as tk
from tkinter import messagebox, ttk

from app import storage


class ClientesFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Gerenciar Clientes", font=("TkDefaultFont", 16, "bold")).pack(pady=15)

        form = tk.Frame(self)
        form.pack(pady=10)

        tk.Label(form, text="Nome do cliente:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.nome_var = tk.StringVar()
        self.nome_entry = tk.Entry(form, textvariable=self.nome_var, width=32)
        self.nome_entry.grid(row=0, column=1, pady=5)
        self.nome_entry.bind("<Return>", self.on_add)

        tk.Label(form, text="Unidade/Localidade (opcional):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.unidade_var = tk.StringVar()
        self.unidade_entry = tk.Entry(form, textvariable=self.unidade_var, width=32)
        self.unidade_entry.grid(row=1, column=1, pady=5)
        self.unidade_entry.bind("<Return>", self.on_add)

        tk.Label(
            form, text="Use a unidade para clientes com mais de um estabelecimento\n"
            "(ex.: mesmo cliente, filiais diferentes).",
            fg="gray", justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5)

        tk.Button(form, text="Adicionar Cliente", command=self.on_add).grid(row=3, column=0, columnspan=2, pady=12)

        self.status_label = tk.Label(self, text="", fg="red")
        self.status_label.pack()

        columns = ("nome", "unidade")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.heading("nome", text="Cliente")
        self.tree.heading("unidade", text="Unidade/Localidade")
        self.tree.column("nome", width=300)
        self.tree.column("unidade", width=240)
        self.tree.pack(pady=10, fill="both", expand=True, padx=20)

        tk.Button(self, text="Remover Selecionado", command=self.on_remove).pack(pady=5)

        tk.Button(self, text="Voltar ao Menu", command=self.on_back_to_menu).pack(side="bottom", pady=15)

    def on_show(self):
        self.nome_var.set("")
        self.unidade_var.set("")
        self.status_label.config(text="", fg="red")
        self.refresh_tree()
        self.nome_entry.focus_set()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        clientes = sorted(storage.listar_clientes(), key=lambda c: (c["nome"].lower(), c["unidade"].lower()))
        for cliente in clientes:
            self.tree.insert("", "end", iid=cliente["id"], values=(cliente["nome"], cliente["unidade"]))

    def on_add(self, event=None):
        nome = self.nome_var.get().strip()
        unidade = self.unidade_var.get().strip()
        if not nome:
            self.status_label.config(text="Informe o nome do cliente.", fg="red")
            return "break"
        clientes = storage.listar_clientes()
        ja_existe = any(
            c["nome"].strip().lower() == nome.lower() and c["unidade"].strip().lower() == unidade.lower()
            for c in clientes
        )
        if ja_existe:
            self.status_label.config(text="Esse cliente (com essa unidade) já está cadastrado.", fg="red")
            return "break"
        storage.adicionar_cliente(nome, unidade)
        self.nome_var.set("")
        self.unidade_var.set("")
        self.status_label.config(text=f"Cliente '{nome}' adicionado.", fg="green")
        self.refresh_tree()
        self.nome_entry.focus_set()
        return "break"

    def try_advance(self):
        self.on_add()

    def on_remove(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um cliente da lista para remover.")
            return
        cliente_id = selecionado[0]
        cliente = next((c for c in storage.listar_clientes() if c["id"] == cliente_id), None)
        if not cliente:
            return
        nome_completo = storage.nome_completo_cliente(cliente)
        if messagebox.askyesno("Confirmar", f"Remover o cliente '{nome_completo}' do cadastro?"):
            storage.remover_cliente(cliente_id)
            self.status_label.config(text=f"Cliente '{nome_completo}' removido.", fg="green")
            self.refresh_tree()

    def on_back_to_menu(self):
        self.controller.show_frame("MainMenu")
