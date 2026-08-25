import tkinter as tk

from app import storage
from app.ui.entrada_estoque import EntradaEstoqueFrame
from app.ui.main_menu import MainMenu
from app.ui.remover_produto import RemoverProdutoFrame
from app.ui.registrar_produto import RegistrarProdutoFrame
from app.ui.saida_estoque import SaidaEstoqueFrame
from app.ui.visualizar_estoque import VisualizarEstoqueFrame


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
            VisualizarEstoqueFrame,
        ):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.current_frame_name = None
        self.bind("<Escape>", self.on_global_escape)
        self.bind("<Return>", self.on_global_enter)

        self.show_frame("MainMenu")

    def show_frame(self, name):
        self.current_frame_name = name
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def on_global_escape(self, event=None):
        """Esc volta ao menu principal, confirmando antes se houver algo em andamento."""
        if self.current_frame_name in (None, "MainMenu"):
            return
        frame = self.frames[self.current_frame_name]
        if hasattr(frame, "on_back_to_menu"):
            frame.on_back_to_menu()

    def on_global_enter(self, event=None):
        """Enter conclui a ação atual (salvar/confirmar/finalizar/avançar), quando aplicável."""
        frame = self.frames.get(self.current_frame_name)
        if frame is not None and hasattr(frame, "try_advance"):
            frame.try_advance()


if __name__ == "__main__":
    storage.ensure_files()
    App().mainloop()
