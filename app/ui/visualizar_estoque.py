from datetime import datetime

import tkinter as tk
from tkinter import ttk

from app import storage
from app.ui.ui_utils import ajustar_largura_pelo_conteudo, habilitar_busca_por_letra

COLUNAS_MOVIMENTOS = ("data_hora", "tipo", "codigo", "nome", "quantidade", "cliente", "data_entrega", "usuario")
HEADERS_MOVIMENTOS = {
    "data_hora": "Data/Hora",
    "tipo": "Tipo",
    "codigo": "Código",
    "nome": "Nome",
    "quantidade": "Qtd.",
    "cliente": "Cliente",
    "data_entrega": "Entrega",
    "usuario": "Usuário",
}
WIDTHS_MOVIMENTOS = {
    "data_hora": 130, "tipo": 70, "codigo": 110, "nome": 200,
    "quantidade": 55, "cliente": 130, "data_entrega": 90, "usuario": 100,
}

COLUNAS_REAIS = ("codigo", "nome", "quantidade")
HEADERS_REAIS = {
    "codigo": "Código",
    "nome": "Nome",
    "quantidade": "Quantidade em Estoque",
}
WIDTHS_REAIS = {"codigo": 150, "nome": 320, "quantidade": 180}


class VisualizarEstoqueFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Visualizar Estoque", font=("TkDefaultFont", 16, "bold")).pack(pady=15)

        filtro_frame = tk.Frame(self)
        filtro_frame.pack(pady=5)

        tk.Label(filtro_frame, text="Tipo:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.tipo_var = tk.StringVar(value="todos")
        self.tipo_combo = ttk.Combobox(
            filtro_frame, textvariable=self.tipo_var, state="readonly", width=10,
            values=["todos", "entrada", "saida"],
        )
        self.tipo_combo.grid(row=0, column=1, padx=5, pady=3)

        tk.Label(filtro_frame, text="Cliente:").grid(row=0, column=2, sticky="e", padx=5, pady=3)
        self.cliente_var = tk.StringVar(value="todos")
        self.cliente_combo = ttk.Combobox(
            filtro_frame, textvariable=self.cliente_var, state="readonly", width=18, values=["todos"],
        )
        self.cliente_combo.grid(row=0, column=3, padx=5, pady=3)
        self.cliente_combo.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros())
        habilitar_busca_por_letra(self.cliente_combo)

        tk.Label(filtro_frame, text="Data (DD/MM/AAAA):").grid(row=0, column=4, sticky="e", padx=5, pady=3)
        self.data_var = tk.StringVar()
        self.data_entry = tk.Entry(filtro_frame, textvariable=self.data_var, width=14)
        self.data_entry.grid(row=0, column=5, padx=5, pady=3)

        tk.Label(filtro_frame, text="Produto:").grid(row=0, column=6, sticky="e", padx=5, pady=3)
        self.produto_var = tk.StringVar(value="todos")
        self.produto_map = {}
        self.produto_combo = ttk.Combobox(
            filtro_frame, textvariable=self.produto_var, state="readonly", width=25, values=["todos"],
        )
        self.produto_combo.grid(row=0, column=7, padx=5, pady=3)
        self.produto_combo.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros())
        habilitar_busca_por_letra(self.produto_combo)

        self.quantidades_reais_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            filtro_frame, text="Quantidades reais", variable=self.quantidades_reais_var,
            command=self.on_toggle_quantidades_reais,
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=(8, 0))

        btn_filtro_frame = tk.Frame(self)
        btn_filtro_frame.pack(pady=5)
        tk.Button(btn_filtro_frame, text="Filtrar", command=self.aplicar_filtros).pack(side="left", padx=5)
        tk.Button(btn_filtro_frame, text="Limpar Filtros", command=self.limpar_filtros).pack(side="left", padx=5)

        self.tree = ttk.Treeview(self, columns=COLUNAS_MOVIMENTOS, show="headings", height=14)
        self._configurar_colunas(COLUNAS_MOVIMENTOS, HEADERS_MOVIMENTOS, WIDTHS_MOVIMENTOS)
        self.tree.pack(pady=10, fill="both", expand=True, padx=20)

        tk.Button(self, text="Voltar ao Menu", command=self.on_back_to_menu).pack(side="bottom", pady=15)

    def on_show(self):
        self.limpar_filtros()

    def limpar_filtros(self):
        self._popular_produtos()
        self._popular_clientes()
        self.tipo_var.set("todos")
        self.cliente_var.set("todos")
        self.data_var.set("")
        self.produto_var.set("todos")
        self.quantidades_reais_var.set(False)
        self._atualizar_estado_filtros()
        self.aplicar_filtros()

    def _popular_produtos(self):
        """Popula o filtro de produto, excluindo caixas (que não aparecem nos registros)."""
        produtos = [p for p in storage.listar_produtos() if p["e_caixa"] != "sim"]
        produtos.sort(key=lambda p: p["nome"].lower())
        self.produto_map = {
            f"{p['nome']} ({p['codigo_barras']})": p["codigo_barras"] for p in produtos
        }
        self.produto_combo.config(values=["todos"] + list(self.produto_map.keys()))
        ajustar_largura_pelo_conteudo(self.produto_combo, minimo=25, maximo=38)

    def _popular_clientes(self):
        """Popula o filtro de cliente com os clientes cadastrados, para casar com o valor exato
        gravado na saída de estoque (evitando divergência de nomes)."""
        clientes = sorted(storage.listar_clientes(), key=lambda c: (c["nome"].lower(), c["unidade"].lower()))
        nomes = [storage.nome_completo_cliente(c) for c in clientes]
        self.cliente_combo.config(values=["todos"] + nomes)
        ajustar_largura_pelo_conteudo(self.cliente_combo, minimo=18, maximo=32)

    def on_toggle_quantidades_reais(self):
        self._atualizar_estado_filtros()
        self.aplicar_filtros()

    def _atualizar_estado_filtros(self):
        desabilitar = self.quantidades_reais_var.get()
        self.tipo_combo.config(state="disabled" if desabilitar else "readonly")
        self.cliente_combo.config(state="disabled" if desabilitar else "readonly")
        self.data_entry.config(state="disabled" if desabilitar else "normal")

    def _configurar_colunas(self, columns, headers, widths):
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=headers[col])
            anchor = "center" if col in ("tipo", "quantidade") else "w"
            self.tree.column(col, width=widths[col], anchor=anchor)

    def aplicar_filtros(self):
        if self.quantidades_reais_var.get():
            self._mostrar_quantidades_reais()
        else:
            self._mostrar_movimentos()

    def _mostrar_movimentos(self):
        self._configurar_colunas(COLUNAS_MOVIMENTOS, HEADERS_MOVIMENTOS, WIDTHS_MOVIMENTOS)
        movimentos = storage.listar_movimentos()

        tipo = self.tipo_var.get()
        if tipo != "todos":
            movimentos = [m for m in movimentos if m["tipo"] == tipo]

        cliente = self.cliente_var.get()
        if cliente and cliente != "todos":
            movimentos = [m for m in movimentos if m["cliente"] == cliente]

        data = self.data_var.get().strip()
        if data:
            data_iso = self._data_para_iso(data)
            movimentos = [m for m in movimentos if m["data_hora"].startswith(data_iso)]

        codigo_produto = self.produto_map.get(self.produto_var.get())
        if codigo_produto:
            movimentos = [m for m in movimentos if m["codigo_barras"] == codigo_produto]

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
                m["usuario"],
            ))

    def _mostrar_quantidades_reais(self):
        self._configurar_colunas(COLUNAS_REAIS, HEADERS_REAIS, WIDTHS_REAIS)
        quantidades = storage.calcular_quantidades_reais()

        codigo_produto = self.produto_map.get(self.produto_var.get())
        if codigo_produto:
            quantidades = [q for q in quantidades if q["codigo_barras"] == codigo_produto]

        self.tree.delete(*self.tree.get_children())
        for produto in quantidades:
            self.tree.insert("", "end", values=(
                produto["codigo_barras"], produto["nome"], produto["quantidade"],
            ))

    @staticmethod
    def _data_para_iso(data_str):
        try:
            return datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return "\0"  # formato inválido: não deve casar com nenhuma linha

    def on_back_to_menu(self):
        self.controller.show_frame("MainMenu")
