import tkinter as tk
from tkinter import messagebox

from app import storage


class RemoverProdutoFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.produto_atual = None

        tk.Label(self, text="Remover Produto", font=("TkDefaultFont", 16, "bold")).pack(pady=15)

        barcode_frame = tk.Frame(self)
        barcode_frame.pack(pady=10)
        tk.Label(barcode_frame, text="Código de barras:").pack(side="left")
        self.barcode_var = tk.StringVar()
        self.barcode_entry = tk.Entry(barcode_frame, textvariable=self.barcode_var, width=30)
        self.barcode_entry.pack(side="left", padx=5)
        self.barcode_entry.bind("<Return>", self.on_barcode_submit)
        tk.Button(barcode_frame, text="Buscar", command=self.on_barcode_submit).pack(side="left")

        self.status_label = tk.Label(self, text="", fg="red")
        self.status_label.pack()

        self.info_frame = tk.Frame(self)
        self.info_labels = {}
        campos = [
            ("nome", "Nome"),
            ("peso_gramas", "Peso (g)"),
            ("e_caixa", "É caixa"),
            ("quantidade_pacotes", "Qtd. pacotes"),
            ("produto_relacionado", "Produto relacionado"),
        ]
        for i, (chave, rotulo) in enumerate(campos):
            tk.Label(self.info_frame, text=f"{rotulo}:").grid(row=i, column=0, sticky="e", pady=3)
            lbl = tk.Label(self.info_frame, text="")
            lbl.grid(row=i, column=1, sticky="w", pady=3)
            self.info_labels[chave] = lbl

        btn_frame = tk.Frame(self.info_frame)
        btn_frame.grid(row=len(campos), column=0, columnspan=2, pady=15)
        tk.Button(btn_frame, text="Confirmar Remoção", width=18, command=self.on_confirm).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", width=15, command=self.on_cancel).pack(side="left", padx=5)

        tk.Button(self, text="Voltar ao Menu", command=self.on_back_to_menu).pack(side="bottom", pady=15)

    def on_show(self):
        self.reset()
        self.barcode_entry.focus_set()

    def reset(self):
        self.produto_atual = None
        self.barcode_var.set("")
        self.status_label.config(text="", fg="red")
        self.info_frame.pack_forget()

    def on_barcode_submit(self, event=None):
        codigo = self.barcode_var.get().strip()
        if not codigo:
            return "break"
        produto = storage.buscar_produto(codigo)
        if not produto:
            self.status_label.config(text="Produto não encontrado.", fg="red")
            self.info_frame.pack_forget()
            self.produto_atual = None
            return "break"
        self.produto_atual = produto
        self.status_label.config(text="Produto encontrado. Confirme a remoção abaixo.", fg="green")
        self.info_labels["nome"].config(text=produto["nome"])
        self.info_labels["peso_gramas"].config(text=produto["peso_gramas"])
        self.info_labels["e_caixa"].config(text="Sim" if produto["e_caixa"] == "sim" else "Não")
        self.info_labels["quantidade_pacotes"].config(text=produto["quantidade_pacotes"] or "-")
        relacionado_texto = "-"
        if produto["e_caixa"] == "sim" and produto.get("produto_relacionado"):
            relacionado = storage.buscar_produto(produto["produto_relacionado"])
            relacionado_texto = relacionado["nome"] if relacionado else produto["produto_relacionado"]
        self.info_labels["produto_relacionado"].config(text=relacionado_texto)
        self.info_frame.pack(pady=10)
        return "break"

    def try_advance(self):
        if self.produto_atual:
            self.on_confirm()

    def on_confirm(self):
        if not self.produto_atual:
            return
        if messagebox.askyesno("Confirmar", f"Remover o produto '{self.produto_atual['nome']}' do cadastro?"):
            storage.remover_produto(self.produto_atual["codigo_barras"])
            messagebox.showinfo("Sucesso", "Produto removido do cadastro.")
            self.reset()
            self.barcode_entry.focus_set()

    def on_cancel(self):
        self.reset()
        self.barcode_entry.focus_set()

    def on_back_to_menu(self):
        if self.produto_atual and not messagebox.askyesno(
            "Atenção", "Existe uma remoção em andamento. Deseja cancelar e voltar ao menu?"
        ):
            return
        self.reset()
        self.controller.show_frame("MainMenu")
