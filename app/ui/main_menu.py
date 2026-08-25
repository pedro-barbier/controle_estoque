import tkinter as tk
from tkinter import font as tkfont, messagebox

from app import storage


class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        title_font = tkfont.Font(size=18, weight="bold")
        tk.Label(self, text="Controle de Estoque - Porto dos Cafés", font=title_font).pack(pady=30)

        btn_font = tkfont.Font(size=12)
        botoes = [
            ("Registrar Produto", "RegistrarProdutoFrame"),
            ("Remover Produto", "RemoverProdutoFrame"),
            ("Registrar para Estoque", "EntradaEstoqueFrame"),
            ("Remover do Estoque", "SaidaEstoqueFrame"),
            ("Visualizar Estoque", "VisualizarEstoqueFrame"),
        ]
        for texto, frame_name in botoes:
            tk.Button(
                self, text=texto, font=btn_font, width=30, height=2,
                command=lambda f=frame_name: controller.show_frame(f),
            ).pack(pady=8)

        tk.Button(
            self, text="Resetar Estoque", font=btn_font, width=30, height=2,
            fg="white", bg="#b03a2e", activeforeground="white", activebackground="#922b21",
            command=self.on_reset_estoque,
        ).pack(pady=(20, 8))

        tk.Button(self, text="Sair", command=controller.destroy).pack(pady=20)

    def on_reset_estoque(self):
        if not messagebox.askyesno(
            "Resetar Estoque",
            "Isso vai apagar TODO o histórico de entradas e saídas do estoque "
            "(as quantidades em estoque voltarão a zero). Os produtos cadastrados "
            "serão mantidos.\n\nEsta ação não pode ser desfeita. Deseja continuar?",
            icon="warning",
        ):
            return
        storage.resetar_estoque()
        messagebox.showinfo("Estoque resetado", "O histórico de entradas e saídas foi apagado.")
