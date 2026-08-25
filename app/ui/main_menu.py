import tkinter as tk
from tkinter import font as tkfont


class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        title_font = tkfont.Font(size=18, weight="bold")
        tk.Label(self, text="Controle de Estoque - Café", font=title_font).pack(pady=30)

        btn_font = tkfont.Font(size=12)
        botoes = [
            ("Registrar Produto", "RegistrarProdutoFrame"),
            ("Remover Produto", "RemoverProdutoFrame"),
            ("Registrar para Estoque", "EntradaEstoqueFrame"),
            ("Remover do Estoque", "SaidaEstoqueFrame"),
        ]
        for texto, frame_name in botoes:
            tk.Button(
                self, text=texto, font=btn_font, width=30, height=2,
                command=lambda f=frame_name: controller.show_frame(f),
            ).pack(pady=8)

        tk.Button(self, text="Sair", command=controller.destroy).pack(pady=20)
