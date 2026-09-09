"""Pequenos utilitários de UI reaproveitados entre telas."""

import tkinter as tk


def manter_foco(entry, condicao=None):
    """Faz `entry` recuperar o foco automaticamente sempre que perdê-lo.

    Pensado para o campo de código de barras nas telas de estoque: como o
    leitor de código digita rápido e finaliza simulando Enter, se o foco
    ficar em outro widget (ex.: a lista, depois de um duplo clique para
    editar quantidade, ou um clique acidental fora do campo) a leitura
    seguinte pode acionar o widget errado (ex.: finalizar o lançamento sem
    querer). `condicao`, quando informada, só permite recuperar o foco se
    retornar True (ex.: checar se essa é a tela/etapa atualmente visível).
    """
    def _ao_perder_foco(event=None):
        def _tentar():
            if condicao is not None and not condicao():
                return
            foco_atual = entry.focus_get()
            if foco_atual is not None and foco_atual.winfo_toplevel() != entry.winfo_toplevel():
                return  # uma janela modal (ex.: diálogo de quantidade) está aberta
            try:
                entry.focus_set()
            except tk.TclError:
                pass
        entry.after(50, _tentar)
    entry.bind("<FocusOut>", _ao_perder_foco)


def ajustar_largura_pelo_conteudo(combo, minimo, maximo):
    """Redimensiona `combo` (campo fechado e lista suspensa, que usam a mesma
    largura no ttk) para caber o maior valor atual, respeitando um mínimo e um
    máximo — evita que nomes longos (ex.: cliente + unidade) fiquem cortados,
    sem estourar o layout quando a combobox divide a linha com outros campos."""
    maior = max((len(v) for v in combo.cget("values")), default=0)
    combo.configure(width=max(minimo, min(maior + 2, maximo)))


def habilitar_busca_por_letra(combo):
    """Ao digitar uma letra num combobox somente-leitura, pula para o primeiro
    valor que começa com essa letra — facilita achar um cliente/produto numa
    lista longa sem precisar rolar manualmente. Funciona tanto com a lista
    fechada quanto aberta; se estiver aberta, ela continua aberta (só a
    seleção pula), para o usuário poder digitar mais letras ou navegar."""
    popdown_listbox_path = {"caminho": None}

    def _sincronizar_listbox_aberta(indice):
        """Atualiza o destaque/scroll da listbox do popdown, se estiver aberta,
        para refletir visualmente o novo valor selecionado."""
        listbox_path = popdown_listbox_path["caminho"]
        if not listbox_path:
            return
        try:
            if not combo.tk.getboolean(combo.tk.eval(f"winfo ismapped {listbox_path}")):
                return
            combo.tk.eval(
                f"{listbox_path} selection clear 0 end; "
                f"{listbox_path} selection set {indice}; "
                f"{listbox_path} activate {indice}; "
                f"{listbox_path} see {indice}"
            )
        except tk.TclError:
            pass

    def _processar(char):
        if not char or not char.isalnum():
            return None
        alvo = char.lower()
        for indice, valor in enumerate(combo.cget("values")):
            if valor.lower().startswith(alvo):
                combo.current(indice)
                combo.event_generate("<<ComboboxSelected>>")
                _sincronizar_listbox_aberta(indice)
                break
        return "break"

    combo.bind("<KeyPress>", lambda event: _processar(event.char))

    # Enquanto a lista está aberta, o teclado vai para a listbox interna do
    # "popdown" — uma janela Tcl separada, criada por baixo dos panos pelo
    # ttk (fora do controle do Tkinter em Python), então precisa de um bind
    # em Tcl "cru" (via .register + tk.call) apontando direto pro caminho
    # dela, senão digitar uma letra com a lista aberta não tem efeito nenhum.
    try:
        popdown = combo.tk.eval(f"ttk::combobox::PopdownWindow {combo}")
        listbox_path = f"{popdown}.f.l"
        popdown_listbox_path["caminho"] = listbox_path
        funcid = combo.register(_processar)
        combo.tk.call("bind", listbox_path, "<KeyPress>", f'if {{"[{funcid} %A]" == "break"}} break')
    except tk.TclError:
        pass
