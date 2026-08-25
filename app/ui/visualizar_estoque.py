from datetime import datetime

import tkinter as tk
from tkinter import ttk

from app import storage


class VisualizarEstoqueFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Visualizar Estoque", font=("TkDefaultFont", 16, "bold")).pack(pady=15)

        filtro_frame = tk.Frame(self)
        filtro_frame.pack(pady=5)

        tk.Label(filtro_frame, text="Tipo:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.tipo_var = tk.StringVar(value="todos")
        ttk.Combobox(
            filtro_frame, textvariable=self.tipo_var, state="readonly", width=10,
            values=["todos", "entrada", "saida"],
        ).grid(row=0, column=1, padx=5, pady=3)

        tk.Label(filtro_frame, text="Cliente:").grid(row=0, column=2, sticky="e", padx=5, pady=3)
        self.cliente_var = tk.StringVar()
        tk.Entry(filtro_frame, textvariable=self.cliente_var, width=18).grid(row=0, column=3, padx=5, pady=3)

        tk.Label(filtro_frame, text="Data (DD/MM/AAAA):").grid(row=0, column=4, sticky="e", padx=5, pady=3)
        self.data_var = tk.StringVar()
        tk.Entry(filtro_frame, textvariable=self.data_var, width=14).grid(row=0, column=5, padx=5, pady=3)

        btn_filtro_frame = tk.Frame(self)
        btn_filtro_frame.pack(pady=5)
        tk.Button(btn_filtro_frame, text="Filtrar", command=self.aplicar_filtros).pack(side="left", padx=5)
        tk.Button(btn_filtro_frame, text="Limpar Filtros", command=self.limpar_filtros).pack(side="left", padx=5)

        columns = ("data_hora", "tipo", "codigo", "nome", "quantidade", "cliente", "data_entrega")
        headers = {
            "data_hora": "Data/Hora",
            "tipo": "Tipo",
            "codigo": "Código",
            "nome": "Nome",
            "quantidade": "Qtd.",
            "cliente": "Cliente",
            "data_entrega": "Entrega",
        }
        widths = {
            "data_hora": 130, "tipo": 70, "codigo": 110, "nome": 200,
            "quantidade": 55, "cliente": 130, "data_entrega": 90,
        }
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=14)
        for col in columns:
            self.tree.heading(col, text=headers[col])
            anchor = "center" if col in ("tipo", "quantidade") else "w"
            self.tree.column(col, width=widths[col], anchor=anchor)
        self.tree.pack(pady=10, fill="both", expand=True, padx=20)

        tk.Button(self, text="Voltar ao Menu", command=self.on_back_to_menu).pack(side="bottom", pady=15)

    def on_show(self):
        self.limpar_filtros()

    def limpar_filtros(self):
        self.tipo_var.set("todos")
        self.cliente_var.set("")
        self.data_var.set("")
        self.aplicar_filtros()

    def aplicar_filtros(self):
        movimentos = storage.listar_movimentos()

        tipo = self.tipo_var.get()
        if tipo != "todos":
            movimentos = [m for m in movimentos if m["tipo"] == tipo]

        cliente = self.cliente_var.get().strip().lower()
        if cliente:
            movimentos = [m for m in movimentos if cliente in m["cliente"].lower()]

        data = self.data_var.get().strip()
        if data:
            data_iso = self._data_para_iso(data)
            movimentos = [m for m in movimentos if m["data_hora"].startswith(data_iso)]

        self.tree.delete(*self.tree.get_children())
        for m in movimentos:
            self.tree.insert("", "end", values=(
                m["data_hora"],
                "Entrada" if m["tipo"] == "entrada" else "Saída",
                m["codigo_barras"],
                m["nome"],
                m["quantidade"],
                m["cliente"],
                m["data_entrega"],
            ))

    @staticmethod
    def _data_para_iso(data_str):
        try:
            return datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return "\0"  # formato inválido: não deve casar com nenhuma linha

    def on_back_to_menu(self):
        self.controller.show_frame("MainMenu")
