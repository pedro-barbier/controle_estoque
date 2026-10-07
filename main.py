import queue
import sys
import tkinter as tk
from tkinter import messagebox

from PIL import ImageTk

from app import bandeja, instancia_unica, recursos, storage, sync, sync_config
from app.ui.clientes import ClientesFrame
from app.ui.entrada_estoque import EntradaEstoqueFrame
from app.ui.login_dialog import LoginDialog
from app.ui.main_menu import MainMenu
from app.ui.remover_produto import RemoverProdutoFrame
from app.ui.registrar_produto import RegistrarProdutoFrame
from app.ui.saida_estoque import SaidaEstoqueFrame
from app.ui.usuarios import UsuariosFrame
from app.ui.visualizar_estoque import VisualizarEstoqueFrame

PROTECTED_FRAMES = {
    "RegistrarProdutoFrame",
    "RemoverProdutoFrame",
    "ClientesFrame",
    "EntradaEstoqueFrame",
    "SaidaEstoqueFrame",
    "UsuariosFrame",
}

# Exigem, além de login, que o usuário logado seja administrador.
ADMIN_FRAMES = {"UsuariosFrame"}


TAMANHOS_ICONE_JANELA = (16, 32, 48, 256)


class App(tk.Tk):
    def __init__(self, fila_comandos):
        super().__init__()
        self.title("Controle de Estoque - Café")
        self.geometry("1080x650")
        self.minsize(950, 550)
        self._aplicar_icone()

        # Comandos vindos de outras threads (menu da bandeja, segunda instância
        # pedindo para mostrar a janela) — consumidos só aqui, na thread do Tk.
        self.fila_comandos = fila_comandos
        self.bandeja_ativa = False
        self._ja_avisou_bandeja = False

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
            UsuariosFrame,
        ):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.current_frame_name = None
        self.usuario_logado = None
        self.bind("<Escape>", self.on_global_escape)
        self.bind("<Return>", self.on_global_enter)

        self.show_frame("MainMenu")
        self.protocol("WM_DELETE_WINDOW", self.on_fechar_janela)
        self.after(200, self._processar_fila)

    def _aplicar_icone(self):
        """Usa icon.png na janela, na barra de tarefas e nos diálogos (Toplevel)."""
        if sys.platform == "win32":
            # Sem isso, rodando sem empacotar, o Windows agrupa a janela sob o
            # ícone do python.exe na barra de tarefas.
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PortoDosCafes.ControleEstoque")
            except Exception:
                pass
        imagens = [recursos.carregar_icone(t) for t in TAMANHOS_ICONE_JANELA]
        if all(imagens):
            self._fotos_icone = [ImageTk.PhotoImage(img, master=self) for img in imagens]
            self.iconphoto(True, *self._fotos_icone)

    def _processar_fila(self):
        try:
            while True:
                comando = self.fila_comandos.get_nowait()
                if comando == "abrir":
                    self.mostrar_janela()
                elif comando == "sair":
                    self.encerrar_completamente()
                    return
        except queue.Empty:
            pass
        self.after(200, self._processar_fila)

    def on_fechar_janela(self):
        """Fechar a janela (X ou botão Fechar) não encerra o programa: ele
        continua na bandeja, para a principal seguir atendendo as secundárias.
        Sair de vez é pelo menu do ícone na bandeja."""
        if self.current_frame_name not in (None, "MainMenu"):
            frame = self.frames[self.current_frame_name]
            if hasattr(frame, "on_back_to_menu"):
                frame.on_back_to_menu()  # pede confirmação se houver itens não finalizados
            if self.current_frame_name != "MainMenu":
                return  # usuário preferiu continuar na tela

        if not self.bandeja_ativa:
            self.encerrar_completamente(confirmar=False)
            return

        self.usuario_logado = None
        self.withdraw()
        if not self._ja_avisou_bandeja:
            self._ja_avisou_bandeja = True
            bandeja.notificar(
                "O controle de estoque continua rodando aqui. "
                "Para encerrar, clique com o botão direito no ícone e escolha Sair."
            )
        sync.sincronizar_em_segundo_plano()

    def mostrar_janela(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        if self.current_frame_name in (None, "MainMenu"):
            self.show_frame("MainMenu")  # atualiza usuário logado/status do sync

    def encerrar_completamente(self, confirmar=True):
        papel = sync_config.carregar()["papel"]
        if confirmar and papel == sync_config.PAPEL_PRINCIPAL:
            self.mostrar_janela()
            if not messagebox.askyesno(
                "Encerrar",
                "Esta é a máquina principal. Enquanto o programa estiver fechado, as máquinas "
                "secundárias não conseguem sincronizar.\n\nDeseja encerrar mesmo assim?",
                icon="warning",
            ):
                return
        sync.parar_sync_periodico()
        sync.sincronizar_conforme_config()
        bandeja.parar()
        instancia_unica.liberar()
        self.destroy()

    def show_frame(self, name):
        if name in PROTECTED_FRAMES and not self.require_login():
            return
        if name in ADMIN_FRAMES and not self.usuario_e_admin():
            messagebox.showerror("Acesso negado", "Apenas administradores podem acessar esta tela.")
            return
        self.current_frame_name = name
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def usuario_e_admin(self):
        return bool(self.usuario_logado) and storage.usuario_e_admin(self.usuario_logado)

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


if __name__ == "__main__":
    _fila_comandos = queue.Queue()
    if not instancia_unica.tentar_ser_primeira(_fila_comandos):
        sys.exit(0)  # já estava rodando (talvez só na bandeja): a janela dele foi mostrada

    storage.ensure_files()

    _config_sync = sync_config.carregar()
    if _config_sync["papel"] == sync_config.PAPEL_PRINCIPAL:
        sync.iniciar_servidor(_config_sync["porta_servidor"])
    else:
        # Na secundária, sincroniza ao abrir; falhas (ex.: principal offline) não bloqueiam o uso.
        sync.sincronizar_conforme_config()
    sync.iniciar_sync_periodico()

    app = App(_fila_comandos)
    app.bandeja_ativa = bandeja.iniciar(_fila_comandos, "Controle de Estoque - Porto dos Cafés")
    if "--bandeja" in sys.argv[1:] and app.bandeja_ativa:
        app.withdraw()  # iniciado junto com o Windows: fica só na bandeja
    app.mainloop()
