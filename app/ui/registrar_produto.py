import tkinter as tk
from tkinter import messagebox, ttk

from app import storage


class RegistrarProdutoFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.codigo_atual = None

        tk.Label(self, text="Registrar Produto", font=("TkDefaultFont", 16, "bold")).pack(pady=15)

        barcode_frame = tk.Frame(self)
        barcode_frame.pack(pady=10)
        tk.Label(barcode_frame, text="Código de barras:").pack(side="left")
        self.barcode_var = tk.StringVar()
        self.barcode_entry = tk.Entry(barcode_frame, textvariable=self.barcode_var, width=30)
        self.barcode_entry.pack(side="left", padx=5)
        self.barcode_entry.bind("<Return>", self.on_barcode_submit)
        tk.Button(barcode_frame, text="Confirmar", command=self.on_barcode_submit).pack(side="left")

        self.status_label = tk.Label(self, text="", fg="red")
        self.status_label.pack()

        self.form_frame = tk.Frame(self)

        tk.Label(self.form_frame, text="Nome do produto:").grid(row=0, column=0, sticky="e", pady=5)
        self.nome_var = tk.StringVar()
        self.nome_entry = tk.Entry(self.form_frame, textvariable=self.nome_var, width=35)
        self.nome_entry.grid(row=0, column=1, pady=5)

        tk.Label(self.form_frame, text="Peso:").grid(row=1, column=0, sticky="e", pady=5)
        peso_sub = tk.Frame(self.form_frame)
        peso_sub.grid(row=1, column=1, sticky="w")
        self.peso_var = tk.StringVar()
        tk.Entry(peso_sub, textvariable=self.peso_var, width=15).pack(side="left")
        self.peso_unidade_var = tk.StringVar(value="g")
        ttk.Combobox(
            peso_sub, textvariable=self.peso_unidade_var, state="readonly", width=5, values=["g", "kg"],
        ).pack(side="left", padx=5)

        tk.Label(self.form_frame, text="É caixa?").grid(row=2, column=0, sticky="e", pady=5)
        self.caixa_var = tk.StringVar(value="nao")
        caixa_sub = tk.Frame(self.form_frame)
        caixa_sub.grid(row=2, column=1, sticky="w")
        tk.Radiobutton(caixa_sub, text="Sim", variable=self.caixa_var, value="sim",
                        command=self.on_caixa_change).pack(side="left")
        tk.Radiobutton(caixa_sub, text="Não", variable=self.caixa_var, value="nao",
                        command=self.on_caixa_change).pack(side="left")

        tk.Label(self.form_frame, text="Quantidade de pacotes:").grid(row=3, column=0, sticky="e", pady=5)
        self.qtd_var = tk.StringVar()
        self.qtd_entry = tk.Entry(self.form_frame, textvariable=self.qtd_var, width=35, state="disabled")
        self.qtd_entry.grid(row=3, column=1, pady=5)

        btn_frame = tk.Frame(self.form_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        tk.Button(btn_frame, text="Salvar", width=15, command=self.on_save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", width=15, command=self.on_cancel).pack(side="left", padx=5)

        tk.Button(self, text="Voltar ao Menu", command=self.on_back_to_menu).pack(side="bottom", pady=15)

    def on_show(self):
        self.reset()
        self.barcode_entry.focus_set()

    def reset(self):
        self.codigo_atual = None
        self.barcode_var.set("")
        self.nome_var.set("")
        self.peso_var.set("")
        self.peso_unidade_var.set("g")
        self.caixa_var.set("nao")
        self.qtd_var.set("")
        self.qtd_entry.config(state="disabled")
        self.status_label.config(text="", fg="red")
        self.form_frame.pack_forget()

    def on_caixa_change(self):
        if self.caixa_var.get() == "sim":
            self.qtd_entry.config(state="normal")
        else:
            self.qtd_var.set("")
            self.qtd_entry.config(state="disabled")

    def on_barcode_submit(self, event=None):
        codigo = self.barcode_var.get().strip()
        if not codigo:
            return "break"
        existente = storage.buscar_produto(codigo)
        if existente:
            self.status_label.config(text=f"Produto já cadastrado: {existente['nome']}", fg="red")
            self.form_frame.pack_forget()
            self.codigo_atual = None
            return "break"
        self.codigo_atual = codigo
        self.status_label.config(text=f"Código lido: {codigo}. Preencha os dados abaixo.", fg="green")
        self.form_frame.pack(pady=10)
        return "break"

    def on_save(self):
        if not self.codigo_atual:
            messagebox.showwarning("Atenção", "Leia um código de barras antes de salvar.")
            return
        nome = self.nome_var.get().strip()
        peso = self.peso_var.get().strip()
        e_caixa = self.caixa_var.get() == "sim"
        qtd = self.qtd_var.get().strip()

        if not nome:
            messagebox.showwarning("Atenção", "Informe o nome do produto.")
            return
        try:
            peso_val = float(peso.replace(",", "."))
        except ValueError:
            messagebox.showwarning("Atenção", "Peso inválido. Use apenas números.")
            return
        if self.peso_unidade_var.get() == "kg":
            peso_val *= 1000
        if e_caixa and (not qtd.isdigit() or int(qtd) <= 0):
            messagebox.showwarning("Atenção", "Informe a quantidade de pacotes (número inteiro maior que zero).")
            return

        storage.adicionar_produto(self.codigo_atual, nome, peso_val, e_caixa, qtd if e_caixa else "")
        messagebox.showinfo("Sucesso", f"Produto '{nome}' cadastrado com sucesso.")
        self.reset()
        self.barcode_entry.focus_set()

    def on_cancel(self):
        self.reset()
        self.barcode_entry.focus_set()

    def try_advance(self):
        if self.codigo_atual:
            self.on_save()

    def on_back_to_menu(self):
        if self.codigo_atual and not messagebox.askyesno(
            "Atenção", "Existe um cadastro em andamento. Deseja cancelar e voltar ao menu?"
        ):
            return
        self.reset()
        self.controller.show_frame("MainMenu")
