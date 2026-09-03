import tkinter as tk
from tkinter import font as tkfont, messagebox

from app import storage, sync, sync_config
from app.ui.sync_config_dialog import SyncConfigDialog


class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        title_font = tkfont.Font(size=18, weight="bold")
        tk.Label(self, text="Controle de Estoque - Porto dos Cafés", font=title_font).pack(pady=(30, 5))

        status_frame = tk.Frame(self)
        status_frame.pack(pady=(0, 15))
        self.usuario_label = tk.Label(status_frame, text="", fg="gray")
        self.usuario_label.pack(side="left", padx=(0, 10))
        tk.Button(status_frame, text="Trocar Usuário", command=self.on_trocar_usuario).pack(side="left")

        sync_frame = tk.Frame(self)
        sync_frame.pack(pady=(0, 15))
        self.sync_status_label = tk.Label(sync_frame, text="", fg="gray")
        self.sync_status_label.pack(side="left", padx=(0, 10))
        self.sync_button = tk.Button(sync_frame, text="Sincronizar Agora", command=self.on_sincronizar)
        self.sync_button.pack(side="left", padx=(0, 5))
        tk.Button(sync_frame, text="Configurar Sincronização", command=self.on_configurar_sync).pack(side="left")

        # Numa máquina secundária, produtos/clientes são sempre substituídos
        # pelos dados da principal a cada sincronização (ver
        # storage.aplicar_dados_sincronizados) — cadastrar ou remover algo
        # aqui seria desfeito no sync seguinte, então essas telas ficam
        # disponíveis só na principal (ou numa máquina isolada, sem sync).
        e_secundaria = sync_config.carregar()["papel"] == sync_config.PAPEL_SECUNDARIA

        btn_font = tkfont.Font(size=12)
        botoes = [
            ("Registrar Produto", "RegistrarProdutoFrame"),
            ("Remover Produto", "RemoverProdutoFrame"),
            ("Gerenciar Clientes", "ClientesFrame"),
            ("Registrar para Estoque", "EntradaEstoqueFrame"),
            ("Remover do Estoque", "SaidaEstoqueFrame"),
            ("Visualizar Estoque", "VisualizarEstoqueFrame"),
        ]
        SOMENTE_PRINCIPAL = {"RegistrarProdutoFrame", "RemoverProdutoFrame", "ClientesFrame"}
        if e_secundaria:
            botoes = [(texto, nome) for texto, nome in botoes if nome not in SOMENTE_PRINCIPAL]
            tk.Label(
                self,
                text="Cadastro de produtos e clientes só fica disponível na máquina principal.",
                fg="gray",
            ).pack(pady=(0, 8))
        for texto, frame_name in botoes:
            tk.Button(
                self, text=texto, font=btn_font, width=30, height=2,
                command=lambda f=frame_name: controller.show_frame(f),
            ).pack(pady=8)

        if not e_secundaria:
            tk.Button(
                self, text="Resetar Estoque", font=btn_font, width=30, height=2,
                fg="white", bg="#b03a2e", activeforeground="white", activebackground="#922b21",
                command=self.on_reset_estoque,
            ).pack(pady=(20, 8))

        tk.Button(self, text="Sair", command=controller.destroy).pack(pady=20)

    def on_show(self):
        self._atualizar_status_usuario()
        self._atualizar_status_sync()

    def _atualizar_status_usuario(self):
        nome = self.controller.usuario_logado
        texto = f"Usuário logado: {nome}" if nome else "Nenhum usuário logado"
        self.usuario_label.config(text=texto)

    def _atualizar_status_sync(self):
        config = sync_config.carregar()
        papel = config["papel"]
        if papel == sync_config.PAPEL_ISOLADO:
            self.sync_status_label.config(text="Sincronização: desativada (uso em uma única máquina)", fg="gray")
            self.sync_button.config(state="disabled")
            return

        self.sync_button.config(state="normal")
        if papel == sync_config.PAPEL_PRINCIPAL:
            self.sync_status_label.config(
                text=f"Servidor de sincronização ativo (porta {config['porta_servidor']})", fg="gray"
            )
            self.sync_button.config(state="disabled")
            return

        status = sync.status_atual()
        if status["quando"] is None:
            self.sync_status_label.config(text="Ainda não sincronizado nesta sessão.", fg="gray")
        else:
            hora = status["quando"].strftime("%H:%M:%S")
            if status["ok"]:
                self.sync_status_label.config(text=f"Sincronizado às {hora}.", fg="gray")
            else:
                self.sync_status_label.config(text=f"Falha ao sincronizar às {hora}: {status['mensagem']}", fg="red")

    def on_sincronizar(self):
        config = sync_config.carregar()
        self.sync_button.config(state="disabled")
        self.sync_status_label.config(text="Sincronizando...", fg="gray")
        self.update_idletasks()
        try:
            resumo = sync.sincronizar_e_registrar(config["principal_ip"], config["principal_porta"])
        except sync.ErroSincronizacao as exc:
            messagebox.showerror("Sincronização", str(exc))
        else:
            messagebox.showinfo(
                "Sincronização",
                "Sincronizado com sucesso.\n\n"
                f"Enviado: {resumo['entradas_enviadas']} entrada(s), {resumo['saidas_enviadas']} saída(s).\n"
                f"Total no estoque: {resumo['total_produtos']} produto(s), "
                f"{resumo['total_entradas']} entrada(s), {resumo['total_saidas']} saída(s).",
            )
        finally:
            self._atualizar_status_sync()

    def on_configurar_sync(self):
        if not self.controller.require_login():
            return
        dialog = SyncConfigDialog(self.controller)
        self.wait_window(dialog)
        self._atualizar_status_sync()

    def on_trocar_usuario(self):
        self.controller.usuario_logado = None
        self._atualizar_status_usuario()
        messagebox.showinfo(
            "Usuário", "Sessão encerrada. Um novo login será pedido na próxima ação que exigir usuário."
        )

    def on_reset_estoque(self):
        if not self.controller.require_login():
            return
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
