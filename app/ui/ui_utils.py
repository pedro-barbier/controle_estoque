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


def habilitar_busca_por_letra(combo):
    """Ao digitar uma letra num combobox somente-leitura, pula para o primeiro
    valor que começa com essa letra — facilita achar um cliente/produto numa
    lista longa sem precisar rolar manualmente."""
    def _ao_digitar(event):
        char = event.char
        if not char or not char.isalnum():
            return
        alvo = char.lower()
        for indice, valor in enumerate(combo.cget("values")):
            if valor.lower().startswith(alvo):
                combo.current(indice)
                combo.event_generate("<<ComboboxSelected>>")
                break
        return "break"
    combo.bind("<KeyPress>", _ao_digitar)
