import tkinter as tk

from app import storage
from app.ui.entrada_estoque import EntradaEstoqueFrame
from app.ui.main_menu import MainMenu
from app.ui.remover_produto import RemoverProdutoFrame
from app.ui.registrar_produto import RegistrarProdutoFrame
from app.ui.saida_estoque import SaidaEstoqueFrame


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Controle de Estoque - Café")
        self.geometry("700x600")
        self.minsize(600, 480)

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (
            MainMenu,
            RegistrarProdutoFrame,
            RemoverProdutoFrame,
            EntradaEstoqueFrame,
            SaidaEstoqueFrame,
        ):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MainMenu")

    def show_frame(self, name):
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()


if __name__ == "__main__":
    storage.ensure_files()
    App().mainloop()
