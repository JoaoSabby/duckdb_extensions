#!/usr/bin/env bash
set -euo pipefail

# Mantém as fontes e a chave efêmera fora da árvore publicada.
projectDir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
workDir=$(mktemp -d)
trap 'rm -rf -- "$workDir"' EXIT
outputDir=$(realpath -m "${1:-dist}")
repoDir="$workDir/repository"
platformDir="$repoDir/v2.0.0/linux_amd64"
mkdir -p "$platformDir" "$repoDir/.well-known" "$repoDir/licenses" "$outputDir"

# Fixa as fontes na mesma revisão do DuckDB usada pelo pacote R 2.0.0.
git clone --depth 1 --branch v2.0.0 https://github.com/duckdb/duckdb.git "$workDir/duckdb"
test "$(git -C "$workDir/duckdb" rev-parse HEAD)" = d54cbbe3df17e8e5ce68312f483b4155836112aa

targets=()
while read -r name url revision; do
  git init -q "$workDir/$name"
  git -C "$workDir/$name" fetch --depth 1 "$url" "$revision"
  git -C "$workDir/$name" checkout --detach FETCH_HEAD

  # As adaptações rastreadas preservam a origem de cada extensão.
  patch="$projectDir/patches/$name.patch"
  if [[ -s $patch ]]; then
    git -C "$workDir/$name" apply "$patch"
  fi

  printf 'include("%s/%s/extension_config.cmake")\n' "$workDir" "$name" >> "$workDir/extensions.cmake"
  targets+=("${name}_loadable_extension")
  cp "$workDir/$name/LICENSE" "$repoDir/licenses/$name.txt"
done < "$projectDir/sources.tsv"

# A ligação estática mantém os binários carregáveis no R sem exportar os símbolos do pacote.
cmake -S "$workDir/duckdb" -B "$workDir/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.10 \
  -DDUCKDB_EXTENSION_CONFIGS="$workDir/extensions.cmake" -DDUCKDB_EXPLICIT_VERSION=v2.0.0 \
  -DEXTENSION_STATIC_BUILD=ON -DBUILD_SHELL=OFF -DBUILD_UNITTESTS=OFF
cmake --build "$workDir/build" --parallel 3 --target "${targets[@]}"

# Assina o conteúdo e substitui apenas os 256 bytes reservados para a assinatura.
(umask 077; openssl genrsa -out "$workDir/private.pem" 2048)
openssl rsa -in "$workDir/private.pem" -pubout -out "$repoDir/public.pem"
python3 - "$repoDir" <<'PY'
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
key = (repo / 'public.pem').read_text()
(repo / '.well-known/duckdb-extension-repo.json').write_text(
    json.dumps({'signature_keys': [key]}, indent=2) + '\n'
)
PY

mkdir -p "$workDir/signed"
while read -r name _; do
  binary="$workDir/build/extension/$name/$name.duckdb_extension"
  unsigned="$workDir/unsigned"
  signed="$workDir/signed/$name.duckdb_extension"
  head -c -256 "$binary" > "$unsigned"
  "$workDir/duckdb/scripts/compute-extension-hash.sh" "$unsigned" > "$workDir/digest"
  openssl pkeyutl -sign -in "$workDir/digest" -inkey "$workDir/private.pem" \
    -pkeyopt digest:sha256 -out "$workDir/signature"
  test "$(wc -c < "$workDir/signature")" -eq 256
  cat "$unsigned" "$workDir/signature" > "$signed"
  gzip -n -c "$signed" > "$platformDir/$name.duckdb_extension.gz"
done < "$projectDir/sources.tsv"
"$workDir/duckdb/scripts/verify-extension-signing.sh" "$workDir/signed" "$repoDir/public.pem"

# Só empacota após instalar e carregar todos os binários com assinatura obrigatória.
curl --fail --silent --show-error --location --retry 3 \
  https://github.com/duckdb/duckdb/releases/download/v2.0.0/duckdb-cli-linux-amd64.tar.gz \
  -o "$workDir/duckdb-cli.tar.gz"
mkdir -p "$workDir/cli"
tar -xzf "$workDir/duckdb-cli.tar.gz" -C "$workDir/cli"
{
  printf "SET extension_directory='%s/extensions';\n" "$workDir"
  printf "SET allow_extension_repositories='allowed';\n"
  printf "CREATE EXTENSION REPOSITORY sabby_local WITH PREFIX '%s';\n" "$repoDir"
  while read -r name _; do
    printf 'INSTALL AND LOAD %s FROM sabby_local;\n' "$name"
  done < "$projectDir/sources.tsv"
  cat "$projectDir/smoke.sql"
} | "$workDir/cli/duckdb" -no-agent -batch -bail

cp "$projectDir/LEIA-ME.md" "$projectDir/sources.tsv" "$projectDir/smoke.sql" "$projectDir/install.R" "$repoDir/"
cp -R "$projectDir/patches" "$repoDir/"
cp "$workDir/duckdb/LICENSE" "$repoDir/licenses/duckdb.txt"
tar -czf "$outputDir/duckdb-local-v2.0.0-linux_amd64.tar.gz" -C "$repoDir" .
(cd "$outputDir" && sha256sum duckdb-local-v2.0.0-linux_amd64.tar.gz > SHA256SUMS)
