# Gerando o executável (Windows)

O aplicativo é escrito em Python puro (Tkinter), sem dependências externas
para rodar. O único passo extra é empacotá-lo em um `.exe` com o
PyInstaller, o que precisa ser feito **em uma máquina Windows** (não é
possível gerar um `.exe` funcional a partir do Linux).

## 1. Pré-requisitos na máquina Windows

- Python 3.10+ instalado (baixe em https://python.org/downloads — marque a
  opção "Add python.exe to PATH" durante a instalação).

## 2. Gerar o executável

1. Copie a pasta inteira do projeto para a máquina Windows.
2. Dê dois cliques em `build_windows.bat` (ou rode-o em um terminal).
3. Aguarde — ele instala o PyInstaller e gera o executável.
4. O resultado fica em `dist\ControleEstoqueCafe.exe`.

## 3. Instalar na loja (ícone na área de trabalho)

1. Crie uma pasta fixa para o programa, por exemplo
   `C:\ControleEstoqueCafe\`.
2. Copie **apenas** o arquivo `dist\ControleEstoqueCafe.exe` para essa
   pasta.
3. Clique com o botão direito no `.exe` → **Enviar para** → **Área de
   trabalho (criar atalho)**.
4. Pronto — o dia a dia é dar dois cliques nesse ícone.

Na primeira execução, o programa cria automaticamente uma pasta `data`
dentro de `C:\ControleEstoqueCafe\` (do lado do `.exe`), com os arquivos
`produtos.csv`, `entradas_estoque.csv` e `saidas_estoque.csv`. **Essa
pasta guarda todo o histórico da loja — não delete nem mova o `.exe` para
fora dela**, ou o programa vai começar do zero.

Para migrar os dados para outra máquina, basta copiar a pasta
`C:\ControleEstoqueCafe\` inteira (executável + pasta `data`).

## 4. Aviso do Windows ao abrir pela primeira vez

Como o executável não tem uma assinatura digital paga, o Windows
Defender SmartScreen pode mostrar um aviso "Windows protegeu o
computador" na primeira execução. Isso é esperado para qualquer programa
não assinado, não é um problema do aplicativo. Para abrir:

1. Clique em **Mais informações**.
2. Clique em **Executar assim mesmo**.

Isso só aparece uma vez por máquina.

## 5. Solução de problemas

**Erro faltando `tcl90.dll` / `tk90.dll` (ou `tcl86t.dll` / `tk86t.dll`)
ao gerar ou abrir o executável:** significa que o PyInstaller não
encontrou as bibliotecas do Tcl/Tk da sua instalação do Python. Isso é
raro em instalações padrão do python.org, mas se acontecer:

1. Localize os arquivos `tcl9*.dll`/`tk9*.dll` (ou `tcl86t.dll`/`tk86t.dll`
   dependendo da versão do Python) dentro da pasta `DLLs` da sua
   instalação do Python.
2. Rode o build manualmente adicionando-os:
   ```
   python -m PyInstaller --onefile --windowed --name ControleEstoqueCafe ^
     --add-binary "C:\Caminho\Para\Python\DLLs\tcl90.dll;." ^
     --add-binary "C:\Caminho\Para\Python\DLLs\tk90.dll;." ^
     main.py
   ```

**Antivírus da loja bloqueia ou apaga o `.exe`:** executáveis gerados
pelo PyInstaller às vezes são sinalizados por falso-positivo (comum em
antivírus mais agressivos). Adicione uma exceção para a pasta
`C:\ControleEstoqueCafe\` no antivírus.

## Testando no Linux (opcional, só para desenvolvimento)

`build_linux.sh` gera um executável equivalente para Linux — útil para
testar mudanças rapidamente sem precisar de uma máquina Windows. Ele não
é o artefato final para a loja.
