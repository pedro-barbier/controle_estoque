#!/usr/bin/env bash
# Gera um executável standalone do Controle de Estoque para Linux.
set -e
cd "$(dirname "$0")"

echo "Instalando o PyInstaller (se necessário)..."
python3 -m pip install --user --upgrade -r requirements-build.txt

echo
echo "Gerando o executável..."

# Em algumas instalações de Python (ex: via mise/pyenv com Tcl/Tk 9.x), o
# PyInstaller não consegue localizar sozinho as bibliotecas do Tcl/Tk.
# Aqui detectamos esse caso e as incluímos manualmente no pacote.
shopt -s nullglob
PY_PREFIX="$(python3 -c 'import sys; print(sys.prefix)')"
EXTRA_ARGS=()
for f in "$PY_PREFIX"/lib/libtcl9*.so "$PY_PREFIX"/lib/libtcl9*.so.*; do
    EXTRA_ARGS+=(--add-binary "$f:.")
done

python3 -m PyInstaller --onefile --windowed --name ControleEstoqueCafe --clean "${EXTRA_ARGS[@]}" main.py

echo
echo "Pronto! Executável gerado em: dist/ControleEstoqueCafe"
echo "Copie esse arquivo para onde quiser usar o programa."
echo "Na primeira execução ele cria uma pasta 'data' ao lado do executável."
