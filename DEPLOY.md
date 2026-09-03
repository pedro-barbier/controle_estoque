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
dentro de `C:\ControleEstoqueCafe\` (do lado do `.exe`), com um único
arquivo de banco de dados `estoque.db`. **Essa pasta guarda todo o
histórico da loja — não delete nem mova o `.exe` para fora dela**, ou o
programa vai começar do zero.

Se a máquina já tinha uma instalação anterior baseada em CSV (`produtos.csv`,
`entradas_estoque.csv`, etc.), a primeira execução da versão atualizada
migra esses dados automaticamente para `estoque.db` — sem nenhum passo
manual — e renomeia os CSVs originais para `.csv.bak` (guardados na mesma
pasta `data`, como backup; nada é apagado).

Para migrar os dados para outra máquina, basta copiar a pasta
`C:\ControleEstoqueCafe\` inteira (executável + pasta `data`, agora com um
único arquivo `estoque.db` em vez de vários `.csv`).

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

## 6. Sincronizando várias máquinas pelo wifi da loja

O programa suporta ter uma máquina **Principal** (onde as entradas/saídas de
estoque são registradas) e outras máquinas **Secundárias** na mesma rede
wifi, usadas para visualizar/conferir o estoque e também podem registrar
lançamentos, que são enviados para a principal ao sincronizar.

Isso é opcional — se a loja usa só uma máquina, não precisa configurar nada
(fica no modo padrão "Não sincronizar").

### Na máquina Principal

1. Abra o programa, clique em **Configurar Sincronização** (pede login).
2. Selecione **Principal** e confirme a porta (padrão `8765` — só mude se
   já usar essa porta para outra coisa).
3. Anote o **IP desta máquina**, mostrado na tela (algo como
   `192.168.15.48`) — vai ser usado para configurar as secundárias.
4. Salve e reinicie o programa.
5. Na primeira vez, o **Firewall do Windows** deve perguntar se permite o
   programa receber conexões na rede — clique em **Permitir acesso**
   (redes privadas/domésticas). Se isso for negado sem querer, as
   secundárias não conseguem sincronizar; para corrigir, procure
   "Permitir um aplicativo pelo Firewall do Windows" no menu Iniciar e
   marque o `ControleEstoqueCafe.exe`.

### Em cada máquina Secundária

1. Abra o programa, clique em **Configurar Sincronização** (pede login).
2. Selecione **Secundária**.
3. Informe o **IP da máquina principal** (anotado no passo acima) e a
   porta (`8765`, se não foi trocada).
4. Opcionalmente, dê um nome a essa máquina (ex.: "Caixa 2") — aparece no
   histórico de movimentações para identificar de onde veio cada
   lançamento.
5. Salve e reinicie o programa.

A partir daí, cada máquina secundária sincroniza automaticamente ao abrir e
ao fechar o programa, e também a qualquer momento pelo botão
**Sincronizar Agora** no menu principal. Se a máquina principal estiver
desligada ou fora da rede no momento, a sincronização falha silenciosamente
(ou mostra o erro, se veio do botão) e o programa continua funcionando
normalmente com os dados que já tinha — nada é perdido, só fica pendente de
envio até a próxima sincronização bem-sucedida.

**Importante:** todas as máquinas precisam estar na mesma rede wifi/local
para se enxergarem. Isso não funciona pela internet.

## Testando no Linux (opcional, só para desenvolvimento)

`build_linux.sh` gera um executável equivalente para Linux — útil para
testar mudanças rapidamente sem precisar de uma máquina Windows. Ele não
é o artefato final para a loja.
