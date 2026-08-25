import tkinter as tk
from tkinter import messagebox, ttk

from app import storage


class EntradaEstoqueFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pendentes = {}  # codigo_barras -> {"nome": str, "quantidade": int}

        tk.Label(self, text="Registrar para Estoque (Entrada)", font=("TkDefaultFont", 16, "bold")).pack(pady=15)

        barcode_frame = tk.Frame(self)
        barcode_frame.pack(pady=5)
        tk.Label(barcode_frame, text="Código de barras:").pack(side="left")
        self.barcode_var = tk.StringVar()
        self.barcode_entry = tk.Entry(barcode_frame, textvariable=self.barcode_var, width=30)
        self.barcode_entry.pack(side="left", padx=5)
        self.barcode_entry.bind("<Return>", self.on_barcode_submit)

        self.status_label = tk.Label(self, text="", fg="red")
        self.status_label.pack()

        columns = ("codigo", "nome", "quantidade")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("codigo", text="Código")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("quantidade", text="Quantidade")
        self.tree.column("codigo", width=150)
        self.tree.column("nome", width=250)
        self.tree.column("quantidade", width=100, anchor="center")
        self.tree.pack(pady=10, fill="both", expand=True, padx=20)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Remover Selecionado", command=self.on_remove_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar Tudo", command=self.on_cancel_all).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Finalizar e Adicionar ao Estoque", command=self.on_finalize).pack(side="left", padx=5)

        tk.Button(self, text="Voltar ao Menu", command=self.on_back_to_menu).pack(side="bottom", pady=15)

    def on_show(self):
        self.reset()
        self.barcode_entry.focus_set()

    def reset(self):
        self.pendentes = {}
        self.barcode_var.set("")
        self.status_label.config(text="", fg="red")
        self.refresh_tree()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for codigo, item in self.pendentes.items():
            self.tree.insert("", "end", iid=codigo, values=(codigo, item["nome"], item["quantidade"]))

    def on_barcode_submit(self, event=None):
        codigo = self.barcode_var.get().strip()
        self.barcode_var.set("")
        if not codigo:
            return
        produto = storage.buscar_produto(codigo)
        if not produto:
            self.status_label.config(text=f"Produto com código {codigo} não cadastrado.", fg="red")
            return
        if codigo in self.pendentes:
            self.pendentes[codigo]["quantidade"] += 1
        else:
            self.pendentes[codigo] = {"nome": produto["nome"], "quantidade": 1}
        self.status_label.config(text=f"Adicionado: {produto['nome']}", fg="green")
        self.refresh_tree()

    def on_remove_selected(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um item da lista para remover.")
            return
        codigo = selecionado[0]
        item = self.pendentes.get(codigo)
        if not item:
            return
        item["quantidade"] -= 1
        if item["quantidade"] <= 0:
            del self.pendentes[codigo]
        self.refresh_tree()

    def on_cancel_all(self):
        if not self.pendentes or messagebox.askyesno("Cancelar", "Descartar todos os itens lidos?"):
            self.reset()
            self.barcode_entry.focus_set()

    def on_finalize(self):
        if not self.pendentes:
            messagebox.showwarning("Atenção", "Nenhum produto lido.")
            return
        itens = [
            {"codigo_barras": c, "nome": i["nome"], "quantidade": i["quantidade"]}
            for c, i in self.pendentes.items()
        ]
        storage.registrar_entrada(itens)
        messagebox.showinfo("Sucesso", "Produtos adicionados ao estoque.")
        self.reset()
        self.barcode_entry.focus_set()

    def on_back_to_menu(self):
        if self.pendentes and not messagebox.askyesno(
            "Atenção", "Existem itens não finalizados. Deseja voltar e descartá-los?"
        ):
            return
        self.reset()
        self.controller.show_frame("MainMenu")
