import tkinter as tk
from tkinter import font as tkfont, messagebox

from app import sync, sync_config


class SyncConfigDialog(tk.Toplevel):
    """Diálogo modal para configurar o papel desta máquina na sincronização
    (isolada / principal / secundária) e, se secundária, o IP da principal."""

    def __init__(self, parent):
        super().__init__(parent)
        self.resultado_salvo = False

        self.title("Configurar Sincronização")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)

        config = sync_config.carregar()

        title_font = tkfont.Font(size=13, weight="bold")
        tk.Label(self, text="Sincronização entre máquinas", font=title_font).grid(
            row=0, column=0, columnspan=2, padx=20, pady=(20, 5)
        )
        tk.Label(
            self,
            text="Todas as máquinas precisam estar na mesma rede wifi.",
            fg="gray",
        ).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15))

        self.papel_var = tk.StringVar(value=config["papel"])
        opcoes = [
            (sync_config.PAPEL_ISOLADO, "Não sincronizar (uso em uma única máquina)"),
            (sync_config.PAPEL_PRINCIPAL, "Principal — grava entradas/saídas de estoque"),
            (sync_config.PAPEL_SECUNDARIA, "Secundária — visualização, conferência e lançamentos"),
        ]
        linha = 2
        for valor, texto in opcoes:
            tk.Radiobutton(
                self, text=texto, variable=self.papel_var, value=valor, command=self._atualizar_campos,
            ).grid(row=linha, column=0, columnspan=2, sticky="w", padx=20)
            linha += 1

        self.frame_principal = tk.Frame(self)
        tk.Label(self.frame_principal, text="Porta do servidor:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        self.porta_servidor_var = tk.StringVar(value=str(config["porta_servidor"]))
        tk.Entry(self.frame_principal, textvariable=self.porta_servidor_var, width=10).grid(
            row=0, column=1, sticky="w"
        )
        self.ip_local_label = tk.Label(self.frame_principal, text="", fg="gray")
        self.ip_local_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

        self.frame_secundaria = tk.Frame(self)
        tk.Label(self.frame_secundaria, text="IP da máquina principal:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        self.principal_ip_var = tk.StringVar(value=config["principal_ip"])
        tk.Entry(self.frame_secundaria, textvariable=self.principal_ip_var, width=16).grid(row=0, column=1, sticky="w")
        tk.Label(self.frame_secundaria, text="Porta:").grid(row=1, column=0, sticky="e", padx=(0, 5), pady=(5, 0))
        self.principal_porta_var = tk.StringVar(value=str(config["principal_porta"]))
        tk.Entry(self.frame_secundaria, textvariable=self.principal_porta_var, width=10).grid(
            row=1, column=1, sticky="w", pady=(5, 0)
        )
        tk.Label(self.frame_secundaria, text="Nome desta máquina (opcional):").grid(
            row=2, column=0, sticky="e", padx=(0, 5), pady=(5, 0)
        )
        self.nome_maquina_var = tk.StringVar(value=config["nome_maquina"])
        tk.Entry(self.frame_secundaria, textvariable=self.nome_maquina_var, width=16).grid(
            row=2, column=1, sticky="w", pady=(5, 0)
        )

        self.frame_principal.grid(row=linha, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")
        self.frame_secundaria.grid(row=linha, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")
        linha += 1

        self.status_label = tk.Label(self, text="", fg="red")
        self.status_label.grid(row=linha, column=0, columnspan=2, pady=(10, 0))
        linha += 1

        botoes = tk.Frame(self)
        botoes.grid(row=linha, column=0, columnspan=2, pady=20)
        tk.Button(botoes, text="Salvar", width=10, command=self.on_salvar).pack(side="left", padx=5)
        tk.Button(botoes, text="Cancelar", width=10, command=self.on_cancel).pack(side="left", padx=5)

        self._atualizar_campos()

        self.update_idletasks()
        largura, altura = self.winfo_reqwidth(), self.winfo_reqheight()
        tela_largura, tela_altura = self.winfo_screenwidth(), self.winfo_screenheight()
        altura = min(altura, tela_altura - 40)
        x = parent.winfo_rootx() + (parent.winfo_width() - largura) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - altura) // 2
        x = max(0, min(x, tela_largura - largura))
        y = max(0, min(y, tela_altura - altura))
        self.geometry(f"{largura}x{altura}+{x}+{y}")

        self.transient(parent)
        self.grab_set()

    def _atualizar_campos(self):
        papel = self.papel_var.get()
        self.frame_principal.grid_remove()
        self.frame_secundaria.grid_remove()
        if papel == sync_config.PAPEL_PRINCIPAL:
            ip = sync.obter_ip_local()
            self.ip_local_label.config(text=f"IP desta máquina: {ip}  (informe esse IP nas máquinas secundárias)")
            self.frame_principal.grid()
        elif papel == sync_config.PAPEL_SECUNDARIA:
            self.frame_secundaria.grid()

    def on_salvar(self, event=None):
        papel = self.papel_var.get()
        try:
            porta_servidor = int(self.porta_servidor_var.get())
            principal_porta = int(self.principal_porta_var.get())
        except ValueError:
            self.status_label.config(text="Porta inválida — use apenas números.")
            return

        if papel == sync_config.PAPEL_SECUNDARIA and not self.principal_ip_var.get().strip():
            self.status_label.config(text="Informe o IP da máquina principal.")
            return

        sync_config.salvar({
            "papel": papel,
            "porta_servidor": porta_servidor,
            "principal_ip": self.principal_ip_var.get().strip(),
            "principal_porta": principal_porta,
            "nome_maquina": self.nome_maquina_var.get().strip(),
        })
        self.resultado_salvo = True
        messagebox.showinfo(
            "Sincronização", "Configuração salva. É preciso reiniciar o programa para aplicar a mudança.",
            parent=self,
        )
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()
