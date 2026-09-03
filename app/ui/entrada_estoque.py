import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app import storage


class EntradaEstoqueFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pendentes = {}  # codigo_barras -> item (ver storage.descrever_item_estoque)

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

        columns = ("codigo", "nome", "tipo", "quantidade")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("codigo", text="Código")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("quantidade", text="Quantidade")
        self.tree.column("codigo", width=140)
        self.tree.column("nome", width=220)
        self.tree.column("tipo", width=150)
        self.tree.column("quantidade", width=90, anchor="center")
        self.tree.pack(pady=10, fill="both", expand=True, padx=20)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        tk.Label(
            self, text="Dica: dê duplo clique em um item para alterar a quantidade manualmente.",
            fg="gray",
        ).pack()

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
            tipo = f"Caixa ({item['quantidade_pacotes']}un/cada)" if item["e_caixa"] else "Produto"
            self.tree.insert("", "end", iid=codigo, values=(codigo, item["nome"], tipo, item["quantidade"]))

    def on_barcode_submit(self, event=None):
        codigo = self.barcode_var.get().strip()
        self.barcode_var.set("")
        if not codigo:
            return "break"
        item = storage.descrever_item_estoque(codigo)
        if not item:
            self.status_label.config(text=f"Produto com código {codigo} não cadastrado.", fg="red")
            return "break"
        if item["e_caixa"] and (not item["produto_relacionado_codigo"] or item["quantidade_pacotes"] <= 0):
            self.status_label.config(
                text="Caixa sem produto relacionado ou quantidade de pacotes inválida.", fg="red",
            )
            return "break"
        chave = item["codigo_barras"]
        if chave in self.pendentes:
            self.pendentes[chave]["quantidade"] += 1
        else:
            self.pendentes[chave] = {**item, "quantidade": 1}
        rotulo = "Caixa adicionada" if item["e_caixa"] else "Adicionado"
        self.status_label.config(text=f"{rotulo}: {item['nome']}", fg="green")
        self.refresh_tree()
        return "break"

    def on_tree_double_click(self, event):
        codigo = self.tree.identify_row(event.y)
        if not codigo or codigo not in self.pendentes:
            return
        item = self.pendentes[codigo]
        unidade = "caixas" if item["e_caixa"] else "unidades"
        nova_qtd = simpledialog.askinteger(
            "Alterar quantidade",
            f"Nova quantidade de {unidade} para '{item['nome']}':",
            initialvalue=item["quantidade"],
            minvalue=0,
            parent=self,
        )
        if nova_qtd is None:
            return
        if nova_qtd == 0:
            del self.pendentes[codigo]
        else:
            item["quantidade"] = nova_qtd
        self.refresh_tree()

    def try_advance(self):
        if self.pendentes:
            self.on_finalize()

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
        itens = storage.expandir_itens_pendentes(self.pendentes)
        storage.registrar_entrada(itens, self.controller.usuario_logado)
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
