import tkinter as tk

from app import storage, sync, sync_config
from app.ui.clientes import ClientesFrame
from app.ui.entrada_estoque import EntradaEstoqueFrame
from app.ui.login_dialog import LoginDialog
from app.ui.main_menu import MainMenu
from app.ui.remover_produto import RemoverProdutoFrame
from app.ui.registrar_produto import RegistrarProdutoFrame
from app.ui.saida_estoque import SaidaEstoqueFrame
from app.ui.visualizar_estoque import VisualizarEstoqueFrame

PROTECTED_FRAMES = {
    "RegistrarProdutoFrame",
    "RemoverProdutoFrame",
    "ClientesFrame",
    "EntradaEstoqueFrame",
    "SaidaEstoqueFrame",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Controle de Estoque - Café")
        self.geometry("1080x650")
        self.minsize(950, 550)

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (
            MainMenu,
            RegistrarProdutoFrame,
            RemoverProdutoFrame,
            ClientesFrame,
            EntradaEstoqueFrame,
            SaidaEstoqueFrame,
            VisualizarEstoqueFrame,
        ):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.current_frame_name = None
        self.usuario_logado = None
        self.bind("<Escape>", self.on_global_escape)
        self.bind("<Return>", self.on_global_enter)

        self.show_frame("MainMenu")

    def show_frame(self, name):
        if name in PROTECTED_FRAMES and not self.require_login():
            return
        self.current_frame_name = name
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def require_login(self):
        """Garante que há um usuário logado, pedindo login se necessário.

        Retorna True se já havia (ou passou a haver) um usuário autenticado,
        False se o login foi cancelado ou falhou.
        """
        if self.usuario_logado:
            return True
        dialog = LoginDialog(self)
        self.wait_window(dialog)
        if dialog.resultado:
            self.usuario_logado = dialog.resultado
            return True
        return False

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


def _sincronizar_silenciosamente():
    """Sincroniza com a máquina principal, se esta máquina for secundária. Chamado ao
    abrir e ao fechar o app; falhas (ex.: principal offline) não bloqueiam o uso do app."""
    config = sync_config.carregar()
    if config["papel"] != sync_config.PAPEL_SECUNDARIA:
        return
    try:
        sync.sincronizar_e_registrar(config["principal_ip"], config["principal_porta"])
    except sync.ErroSincronizacao:
        pass


if __name__ == "__main__":
    storage.ensure_files()

    _config_sync = sync_config.carregar()
    if _config_sync["papel"] == sync_config.PAPEL_PRINCIPAL:
        sync.iniciar_servidor(_config_sync["porta_servidor"])
    else:
        _sincronizar_silenciosamente()

    app = App()
    app.protocol("WM_DELETE_WINDOW", lambda: (_sincronizar_silenciosamente(), app.destroy()))
    app.mainloop()
