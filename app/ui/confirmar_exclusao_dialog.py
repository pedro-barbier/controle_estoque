import tkinter as tk
from tkinter import font as tkfont, ttk

COLUNAS = ("data_hora", "tipo", "codigo", "nome", "quantidade", "cliente", "usuario")
HEADERS = {
    "data_hora": "Data/Hora",
    "tipo": "Tipo",
    "codigo": "Código",
    "nome": "Nome",
    "quantidade": "Qtd.",
    "cliente": "Cliente",
    "usuario": "Usuário",
}
WIDTHS = {
    "data_hora": 130, "tipo": 70, "codigo": 110, "nome": 200,
    "quantidade": 55, "cliente": 130, "usuario": 100,
}


class ConfirmarExclusaoDialog(tk.Toplevel):
    """Diálogo modal que resume as entradas/saídas selecionadas na visualização
    de estoque e pede confirmação antes de excluí-las. Após fechar,
    `confirmado` é True se o usuário clicou em Excluir."""

    def __init__(self, parent, movimentos):
        super().__init__(parent)
        self.confirmado = False

        self.title("Confirmar Exclusão")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)

        total_entradas = sum(1 for m in movimentos if m["tipo"] == "entrada")
        total_saidas = len(movimentos) - total_entradas

        title_font = tkfont.Font(size=13, weight="bold")
        tk.Label(self, text="Excluir registros do estoque", font=title_font).pack(padx=20, pady=(20, 5))
        tk.Label(
            self,
            text=f"{len(movimentos)} registro(s) selecionado(s): "
                 f"{total_entradas} entrada(s) e {total_saidas} saída(s).",
        ).pack(padx=20)

        lista_frame = tk.Frame(self)
        lista_frame.pack(padx=20, pady=10, fill="both", expand=True)
        tree = ttk.Treeview(
            lista_frame, columns=COLUNAS, show="headings", height=min(max(len(movimentos), 3), 12),
            selectmode="none",
        )
        scrollbar = ttk.Scrollbar(lista_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        for col in COLUNAS:
            tree.heading(col, text=HEADERS[col])
            tree.column(col, width=WIDTHS[col], anchor="center" if col in ("tipo", "quantidade") else "w")
        for m in movimentos:
            tree.insert("", "end", values=(
                m["data_hora"],
                "Entrada" if m["tipo"] == "entrada" else "Saída",
                m["codigo_barras"],
                m["nome"],
                m["quantidade"],
                m["cliente"],
                m["usuario"],
            ))
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(
            self,
            text="As quantidades em estoque serão recalculadas sem esses registros.\n"
                 "Esta ação não pode ser desfeita. Deseja continuar?",
            fg="#b03a2e",
        ).pack(padx=20, pady=(0, 5))

        botoes = tk.Frame(self)
        botoes.pack(pady=(10, 20))
        tk.Button(
            botoes, text="Excluir", width=10, command=self.on_confirmar,
            fg="white", bg="#b03a2e", activeforeground="white", activebackground="#922b21",
        ).pack(side="left", padx=5)
        cancelar = tk.Button(botoes, text="Cancelar", width=10, command=self.on_cancel)
        cancelar.pack(side="left", padx=5)

        self.update_idletasks()
        largura, altura = self.winfo_reqwidth(), self.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - largura) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - altura) // 2
        self.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")

        self.transient(parent)
        self.grab_set()
        cancelar.focus_set()

    def on_confirmar(self):
        self.confirmado = True
        self.destroy()

    def on_cancel(self, event=None):
        self.confirmado = False
        self.destroy()
