@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Gerando o executavel do Controle de Estoque
echo ============================================
echo.

echo Instalando o PyInstaller (se necessario)...
python -m pip install --upgrade -r requirements-build.txt
if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel instalar o PyInstaller.
    echo Verifique se o Python esta instalado e disponivel no PATH.
    pause
    exit /b 1
)

echo.
echo Gerando o executavel (isso pode levar um minuto)...
python -m PyInstaller --onefile --windowed --name ControleEstoqueCafe --clean main.py
if errorlevel 1 (
    echo.
    echo ERRO: falha ao gerar o executavel. Veja a mensagem acima.
    echo Se o erro mencionar um arquivo .dll faltando de tcl/tk
    echo (ex: tcl90.dll, tk90.dll), veja o arquivo DEPLOY.md
    echo na secao "Solucao de problemas".
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Pronto!
echo  Executavel gerado em: dist\ControleEstoqueCafe.exe
echo ============================================
echo.
echo Copie esse arquivo (sozinho, sem mais nada) para onde quiser
echo usar o programa, por exemplo a Area de Trabalho.
echo.
echo Na primeira vez que for aberto, ele cria uma pasta "data" do
echo lado do executavel com os arquivos de produtos, entradas e
echo saidas. Essa pasta "data" deve sempre ficar junto do .exe.
echo.
pause
