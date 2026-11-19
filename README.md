# Espelho centralizado de extensões DuckDB

Este repositório reúne, em um único projeto no GitHub, binários de extensões dos
catálogos **Core** e **Community** do DuckDB e de projetos selecionados da
**Query.Farm** e da **NeueSQL**. A centralização permite baixar os artefatos de uma mesma versão e
plataforma, preparar instalações em ambientes isolados e localizar a documentação
original de cada extensão.

O espelho é configurado para **DuckDB v2.0.0 em Linux x86-64 (`linux_amd64`)**.
O workflow utiliza as listas de extensões configuradas no YAML, consulta os binários da
combinação configurada e verifica a integridade dos arquivos gzip. Os artefatos
são publicados nas [Releases do repositório](https://github.com/JoaoSabby/duckdb_extensions/releases) depois de uma
sincronização com publicação habilitada. A assinatura original acompanha o
binário. O DuckDB verifica a assinatura ao instalar ou carregar a extensão.
Os binários sem assinatura da NeueSQL são publicados em uma Release separada.

Os exemplos abaixo formam uma seleção de aplicações bancárias. O inventário
publicado nas Releases é a referência para a disponibilidade de todos os
artefatos, inclusive os que ainda não têm exemplos neste guia.

## Instalação e sincronização

Confira a versão e a plataforma do **mesmo cliente** que executará o SQL.
No R, rode estas consultas na conexão DuckDB usada pelo projeto.

```sql
SELECT version();
PRAGMA platform;
```

### Instalar Core pelo espelho

O exemplo baixa `json` da [Release de Core e Community](https://github.com/JoaoSabby/duckdb_extensions/releases/tag/extensions-v2.0.0-linux_amd64).
A descompactação produz o arquivo que pode ser transferido para um ambiente sem
internet. Execute o SQL no diretório onde o arquivo foi descompactado.

```bash
versao='v2.0.0'
plataforma='linux_amd64'
extensao='json'
base='https://github.com/JoaoSabby/duckdb_extensions/releases/download'
tag="extensions-${versao}-${plataforma}"
arquivo="${extensao}.duckdb_extension"

curl -fL "${base}/${tag}/${arquivo}.gz" -o "${arquivo}.gz" &&
  gzip -dk "${arquivo}.gz"
```

```sql
INSTALL './json.duckdb_extension';
LOAD json;
```

Para outra extensão Core, ajuste o nome no download e nos comandos SQL. As
subseções de aplicação também trazem a instalação na origem, útil quando a
Release do espelho ainda não foi publicada.
[Instalação por arquivo na documentação DuckDB](https://duckdb.org/docs/2.0/extensions/advanced_installation_methods).

### Instalar Community pelo espelho

Para arquivos assinados pelo Community, prepare um repositório local nomeado
com as chaves públicas da versão do DuckDB. O exemplo usa o arquivo
[`yaml`](v2.0.0/linux_amd64/yaml.duckdb_extension.gz) já disponível na árvore do
projeto. Para outra extensão, use seu arquivo na Release de Core e Community.
A extensão [`dq`](v2.0.0/linux_amd64/dq.duckdb_extension.gz) também está na árvore.

```bash
repositorio="$PWD/community_espelho"
destino="${repositorio}/v2.0.0/linux_amd64"
projeto='https://raw.githubusercontent.com/JoaoSabby/duckdb_extensions'
fonte='https://raw.githubusercontent.com/duckdb/duckdb/v2.0.0'

mkdir -p "${repositorio}/.well-known" "${destino}" &&
  curl -fL "${projeto}/main/v2.0.0/linux_amd64/yaml.duckdb_extension.gz" \
    -o "${destino}/yaml.duckdb_extension.gz" &&
  gzip -dk "${destino}/yaml.duckdb_extension.gz" &&
  curl -fL "${fonte}/src/main/extension/extension_helper.cpp" \
    -o "${repositorio}/extension_helper.cpp" &&
  python3 - "${repositorio}" <<'PY_KEYS'
import json
import re
import sys
from pathlib import Path

repository = Path(sys.argv[1])

# Extract only the keys that DuckDB classifies as Community
source = (repository / "extension_helper.cpp").read_text(encoding="utf-8")
community = source.split("community_public_keys[] = {", 1)[1].split("};", 1)[0]
keys = re.findall(
    r"-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----",
    community,
    flags=re.S,
)
if not keys:
    raise SystemExit("Nenhuma chave Community encontrada no código-fonte DuckDB")

key_document = repository / ".well-known" / "duckdb-extension-repo.json"
key_document.write_text(json.dumps({"signature_keys": keys}), encoding="utf-8")
PY_KEYS
```

Transfira o diretório preparado para o ambiente de destino e ajuste o caminho
absoluto no SQL. Nas demais subseções Community, instale e carregue a extensão
com `FROM community_espelho` após preparar o respectivo binário no diretório.

```sql
SET allow_extension_repositories = 'allowed';

CREATE EXTENSION REPOSITORY IF NOT EXISTS community_espelho
    WITH PREFIX '/caminho/absoluto/community_espelho';

INSTALL yaml FROM community_espelho;
LOAD yaml FROM community_espelho;
```

[Chaves originais no código-fonte do DuckDB v2.0.0](https://github.com/duckdb/duckdb/blob/v2.0.0/src/main/extension/extension_helper.cpp) ·
[Documentação de repositórios nomeados](https://duckdb.org/docs/2.0/extensions/extension_repositories).

### Instalar extensões assinadas pela Query.Farm

As subseções da Query.Farm usam o repositório nomeado `query_farm`. Para instalar
diretamente do desenvolvedor, registre-o uma vez no cliente DuckDB.

```sql
SET allow_extension_repositories = 'allowed';

CREATE EXTENSION REPOSITORY IF NOT EXISTS query_farm
    WITH PREFIX 'https://duckdb-extensions.query.farm';
```

Para usar a [Release Query.Farm do espelho](https://github.com/JoaoSabby/duckdb_extensions/releases/tag/query-farm-v2.0.0-linux_amd64)
em ambiente isolado, baixe o documento público de chaves e os binários desejados.
O exemplo prepara a extensão `a5`.

```bash
base='https://github.com/JoaoSabby/duckdb_extensions/releases/download'
tag='query-farm-v2.0.0-linux_amd64'
repositorio="$PWD/query_farm"
destino="${repositorio}/v2.0.0/linux_amd64"

mkdir -p "${repositorio}/.well-known" "${destino}" &&
  curl -fL "${base}/${tag}/duckdb-extension-repo.json" \
    -o "${repositorio}/.well-known/duckdb-extension-repo.json" &&
  curl -fL "${base}/${tag}/a5.duckdb_extension.gz" \
    -o "${destino}/a5.duckdb_extension.gz" &&
  gzip -dk "${destino}/a5.duckdb_extension.gz"
```

Compare as impressões digitais das chaves com a fonte da Query.Farm. No cliente
isolado, substitua `/caminho/absoluto/query_farm` pelo diretório preparado.
Use `FROM query_farm_espelho` nos comandos de instalação e carga das subseções.

```sql
SET allow_extension_repositories = 'allowed';

CREATE EXTENSION REPOSITORY IF NOT EXISTS query_farm_espelho
    WITH PREFIX '/caminho/absoluto/query_farm';

INSTALL a5 FROM query_farm_espelho;
LOAD a5 FROM query_farm_espelho;
```

[Repositório de extensões da Query.Farm](https://query.farm/blog/duckdb-2-query-farm-repository/) ·
[Verificação de chaves no DuckDB](https://duckdb.org/docs/2.0/extensions/extension_repositories).

### Atualização do espelho

A execução agendada ocorre aos domingos, às 03h UTC, meia-noite no horário de
Brasília. Em **Actions → Sync DuckDB Extensions → Run workflow**, a execução manual
valida os downloads. Marque **publish** e selecione a branch padrão para publicar
os artefatos. O relatório da execução lista os downloads indisponíveis e as
falhas. [Workflow de sincronização](.github/workflows/sync_extensions.yml).

## Leitura de arquivos e armazenamento

### `json` · mensagens transacionais e Open Finance

Lê e escreve JSON e extrai campos por caminho. O exemplo transforma uma mensagem
sintética de pagamento Pix em uma linha com valor monetário tipado.

```sql
INSTALL json FROM core;
LOAD json;

WITH eventos(payload) AS (
    VALUES ('{"id":"PIX-001","canal":"PIX","valor":125.90}'::JSON)
)
SELECT
    payload ->> '$.id' AS id_transacao,
    payload ->> '$.canal' AS canal,
    (payload ->> '$.valor')::DECIMAL(15,2) AS valor
FROM eventos;
```

Fonte do desenvolvedor · [DuckDB, suporte a JSON](https://duckdb.org/docs/2.0/data/json/overview).

### `parquet` · histórico transacional

Lê e grava Parquet, um formato colunar adequado a consultas que selecionam apenas
parte das colunas ou linhas. O exemplo cria um arquivo sintético e agrega o
volume de pagamentos por canal. Execute em um diretório gravável.

```sql
INSTALL parquet FROM core;
LOAD parquet;

COPY (
    SELECT canal, valor::DECIMAL(15,2) AS valor
    FROM (VALUES ('PIX', 125.90), ('PIX', 70.00), ('TED', 950.00)) AS t(canal, valor)
) TO 'pagamentos_demo.parquet' (FORMAT parquet);

SELECT canal, count(*) AS quantidade, sum(valor) AS volume
FROM read_parquet('pagamentos_demo.parquet')
GROUP BY canal;
```

Fonte do desenvolvedor · [DuckDB, Parquet](https://duckdb.org/docs/2.0/data/parquet/overview).

### `excel` · conciliação com planilhas

Lê e grava arquivos `.xlsx`. Neste exemplo, a aba `Lancamentos` contém as colunas
`id_lancamento`, `valor_contabil` e `valor_liquidado`. A consulta sinaliza diferenças
e valores ausentes ou inválidos após conversão para decimal.

```sql
INSTALL excel FROM core;
LOAD excel;

WITH importacao AS (
    SELECT
        id_lancamento,
        try_cast(valor_contabil AS DECIMAL(15,2)) AS valor_contabil,
        try_cast(valor_liquidado AS DECIMAL(15,2)) AS valor_liquidado
    FROM read_xlsx('conciliacao.xlsx', sheet = 'Lancamentos', header = true)
)
SELECT *, valor_contabil - valor_liquidado AS diferenca
FROM importacao
WHERE valor_contabil IS NULL
   OR valor_liquidado IS NULL
   OR valor_contabil <> valor_liquidado;
```

Fonte do desenvolvedor · [DuckDB, Excel](https://duckdb.org/docs/2.0/core_extensions/excel).

### `yaml` · configuração de regras

Interpreta documentos YAML e extrai parâmetros tipados. O exemplo lê a versão
e o limite de exposição de uma política sintética de crédito.

```sql
INSTALL yaml FROM community;
LOAD yaml;

WITH politicas(configuracao) AS (
    VALUES (yaml(E'versao: 3\nlimite_exposicao: 25000.00'))
)
SELECT
    yaml_value(configuracao, '$.versao')::INTEGER AS versao_politica,
    yaml_value(configuracao, '$.limite_exposicao')::DECIMAL(15,2) AS limite_exposicao
FROM politicas;
```

Fonte do desenvolvedor · [teaguesterling/duckdb_yaml](https://github.com/teaguesterling/duckdb_yaml).

### `ducklake` · tabelas analíticas de risco

Gerencia tabelas analíticas com catálogo transacional e dados em Parquet. O exemplo
cria uma tabela sintética de exposição em um catálogo DuckLake local, em diretório
gravável. Para repetir no mesmo catálogo, use outro nome de tabela ou um catálogo novo.

```sql
INSTALL ducklake FROM core;
LOAD ducklake;

ATTACH 'ducklake:risco_demo.ducklake' AS risco;

CREATE TABLE risco.main.exposicoes AS
SELECT
    DATE '2026-10-31' AS data_base,
    'capital_de_giro' AS carteira,
    120000.00::DECIMAL(15,2) AS exposicao;

SELECT carteira, sum(exposicao) AS exposicao_total
FROM risco.main.exposicoes
GROUP BY carteira;
```

Fonte do desenvolvedor · [DuckLake, instalação e conexão](https://ducklake.select/docs/stable/duckdb/installation) ·
[DuckLake no GitHub](https://github.com/duckdb/ducklake).

## Integração com sistemas de dados

### `httpfs` · arquivos de dados remotos

Acessa arquivos por HTTP(S) e armazenamento compatível com S3. Para Parquet via
HTTPS, o DuckDB pode solicitar apenas os intervalos exigidos pela consulta.
Substitua a URL ilustrativa por um endereço de homologação que disponibilize o
arquivo e as colunas do exemplo.

```sql
INSTALL httpfs FROM core;
LOAD httpfs;

SELECT adquirente, count(*) AS registros, sum(valor_liquido) AS total_liquidado
FROM read_parquet('https://dados.example.com/liquidacoes/2026-10.parquet')
GROUP BY adquirente;
```

Fonte do desenvolvedor · [DuckDB, acesso HTTPS com HTTPFS](https://duckdb.org/docs/2.0/core_extensions/httpfs/https).

### `postgres` · consulta a bases operacionais

Acessa tabelas PostgreSQL diretamente. O exemplo agrega o saldo das parcelas
vencidas em uma réplica de homologação. Configure a autenticação do PostgreSQL
antes de executar e ajuste o endereço, o usuário e o esquema à instalação.

```sql
INSTALL postgres FROM core;
LOAD postgres;

ATTACH 'host=replica.example.com dbname=credito user=leitor sslmode=verify-full'
    AS credito (TYPE postgres, READ_ONLY);

SELECT carteira, sum(saldo_devedor) AS saldo_vencido
FROM credito.public.parcelas
WHERE situacao = 'VENCIDA'
GROUP BY carteira;
```

Fonte do desenvolvedor · [DuckDB, extensão PostgreSQL](https://duckdb.org/docs/2.0/core_extensions/postgres/overview) ·
[DuckDB PostgreSQL no GitHub](https://github.com/duckdb/duckdb-postgres).

### `oraduck` · carga direta no Oracle

Carrega resultados do DuckDB em uma tabela Oracle existente pela API OCI Direct
Path. Prepare o Oracle Instant Client e a conexão de homologação conforme o
projeto. Substitua os valores ilustrativos no segredo e crie previamente
`RISCO_HML.ML_SCORE_LOTE` com colunas compatíveis com o exemplo. A carga a seguir
grava duas linhas no destino.

```sql
INSTALL oraduck FROM community;
LOAD oraduck;

CREATE SECRET oracle_hml (
    TYPE oraduck,
    USER 'USUARIO_HML',
    PASSWORD 'SUBSTITUIR_NA_SESSAO',
    DSN 'oracle.example.com:1521/HML'
);

COPY (
    SELECT id_cliente, score::DECIMAL(8,4) AS score
    FROM (VALUES (101, 0.0810), (102, 0.1270)) AS t(id_cliente, score)
) TO 'RISCO_HML.ML_SCORE_LOTE' (FORMAT oraduck, CONNECTION 'oracle_hml');
```

Fonte do desenvolvedor · [hugues31/oraduck](https://github.com/hugues31/oraduck).

### `airport` · federação via Arrow Flight

Expõe dados de um servidor Arrow Flight como catálogo DuckDB. O exemplo resume
autorizações por bandeira em um serviço de homologação. Substitua o endereço e
configure a autenticação e o catálogo conforme o serviço.

```sql
INSTALL airport FROM query_farm;
LOAD airport FROM query_farm;

ATTACH 'grpc+tls://flight.example.com:8815' AS cartoes (TYPE airport);

SELECT bandeira, count(*) AS autorizacoes
FROM cartoes.public.autorizacoes
WHERE data_referencia = DATE '2026-10-31'
GROUP BY bandeira;
```

Fonte do desenvolvedor · [Airport, documentação do projeto](https://airport.query.farm/) ·
[Query-farm/airport](https://github.com/Query-farm/airport).

## Qualidade, contratos e auditoria

### `dq` · regras de qualidade em tabelas

Executa asserções SQL sobre tabelas e gera resultados de qualidade consultáveis.
O lote sintético abaixo contém um identificador Pix duplicado. Abra uma base de
teste, por exemplo `duckdb qualidade_demo.duckdb`, e execute o bloco na mesma sessão.

```sql
INSTALL dq FROM community;
LOAD dq;

CREATE OR REPLACE TABLE pagamentos_dq AS
SELECT *
FROM (VALUES ('PIX-001', 125.90), ('PIX-001', 70.00)) AS t(id_pagamento, valor);

SELECT *
FROM expect_unique('pagamentos_dq', 'id_pagamento');
```

Fonte do desenvolvedor · [alitrack/duckdb_dq](https://github.com/alitrack/duckdb_dq).

### `json_schema` · validação de contratos de eventos

Valida documentos contra JSON Schema. O exemplo identifica o evento de
liquidação que viola o contrato por informar o valor como texto.

```sql
INSTALL json_schema FROM query_farm;
LOAD json_schema FROM query_farm;

WITH eventos(id, documento) AS (
    VALUES (1, '{"valor":125.90}'::JSON), (2, '{"valor":"125.90"}'::JSON)
)
SELECT id
FROM eventos
WHERE NOT json_schema_is_valid(
    '{"type":"object","required":["valor"],"properties":{"valor":{"type":"number"}}}',
    documento
);
```

Fonte do desenvolvedor · [Query.Farm, JSON Schema para DuckDB 2.0](https://query.farm/blog/json-schema-for-duckdb-2/) ·
[Query-farm/json_schema](https://github.com/Query-farm/json_schema).

### `icu` · fechamento diário em horário local

Acrescenta suporte a fusos horários, calendários e colações. O exemplo converte o
instante de liquidação em UTC para a data operacional de São Paulo. O pagamento
feito às 01h30 UTC de 1º de novembro ainda pertence a 31 de outubro em São Paulo.

```sql
INSTALL icu FROM core;
LOAD icu;

SELECT timezone(
    'America/Sao_Paulo',
    TIMESTAMPTZ '2026-11-01 01:30:00+00'
)::DATE AS data_operacional;
```

Fonte do desenvolvedor · [DuckDB, extensão ICU](https://duckdb.org/docs/2.0/core_extensions/icu).

## Risco de crédito e prevenção a fraudes

### `infera` · inferência de modelos em SQL

Executa modelos ONNX dentro do DuckDB. O exemplo aplica um modelo de risco a uma
proposta sintética. Forneça `risco_credito.onnx` com três atributos numéricos na
ordem abaixo e uma saída escalar por registro. Preserve a transformação e a
ordem das variáveis usadas no treinamento.

```sql
INSTALL infera FROM community;
LOAD infera;

SELECT infera_load_model('risco_credito', './risco_credito.onnx');

WITH carteira(id_cliente, renda_mensal, comprometimento_renda, meses_relacionamento) AS (
    VALUES (101, 5200.0, 0.27, 48)
)
SELECT
    id_cliente,
    infera_predict(
        'risco_credito', renda_mensal, comprometimento_renda, meses_relacionamento
    ) AS escore
FROM carteira;

SELECT infera_unload_model('risco_credito');
```

Fonte do desenvolvedor · [CogitatorTech/infera](https://github.com/CogitatorTech/infera).

### `duckpgq` · rastreamento de transferências

Implementa consultas SQL/PGQ sobre grafos construídos a partir de tabelas
relacionais. O exemplo encontra contas alcançáveis em até dois saltos a partir da
conta 101, como etapa exploratória de uma investigação.

```sql
INSTALL duckpgq FROM community;
LOAD duckpgq;

CREATE TABLE contas_pgq (id BIGINT PRIMARY KEY);
INSERT INTO contas_pgq VALUES (101), (102), (103);

CREATE TABLE transferencias_pgq (origem BIGINT, destino BIGINT);
INSERT INTO transferencias_pgq VALUES (101, 102), (102, 103);

SET active_grammar_extensions = ['duckpgq'];

CREATE PROPERTY GRAPH rede_pix
    VERTEX TABLES (contas_pgq LABEL conta)
    EDGE TABLES (
        transferencias_pgq
        SOURCE KEY (origem) REFERENCES contas_pgq (id)
        DESTINATION KEY (destino) REFERENCES contas_pgq (id)
        LABEL transferencia
    );

SELECT DISTINCT conta_destino
FROM GRAPH_TABLE (
    rede_pix
    MATCH (a:conta)-[t:transferencia]->{1,2}(b:conta)
    WHERE a.id = 101
    COLUMNS (b.id AS conta_destino)
)
ORDER BY conta_destino;
```

Fonte do desenvolvedor · [DuckPGQ, documentação do projeto](https://duckpgq.org/) ·
[cwida/duckpgq-extension](https://github.com/cwida/duckpgq-extension).

## Séries temporais e indicadores financeiros

### `talib` · indicadores TA-Lib e atributos temporais

Integra funções da TA-Lib para médias móveis, momentum, volatilidade e padrões
de preços. O projeto de origem chama-se `atm_talib`; o nome usado em `INSTALL`
e `LOAD` é `talib`. A origem NeueSQL participa da sincronização semanal por
meio de `NEUESQL_EXTENSIONS: talib`.

O binário sem assinatura é publicado na
[Release NeueSQL do espelho](https://github.com/JoaoSabby/duckdb_extensions/releases/tag/neuesql-v2.0.0-linux_amd64),
separado dos artefatos Core, Community e Query.Farm. Para preparar a instalação
offline de DuckDB v2.0.0/Linux x86-64:

```bash
base='https://github.com/JoaoSabby/duckdb_extensions/releases/download'
tag='neuesql-v2.0.0-linux_amd64'
arquivo='talib.duckdb_extension'

curl -fL "${base}/${tag}/${arquivo}.gz" -o "${arquivo}.gz" &&
  gzip -dk "${arquivo}.gz"

# Habilita a carga do binario sem assinatura nesta instancia do cliente
duckdb -unsigned
```

Transfira o arquivo descompactado ao ambiente de destino. Na sessão iniciada
com `-unsigned`, execute a instalação e o exemplo sintético de média móvel
do saldo de uma conta:

```sql
INSTALL './talib.duckdb_extension';
LOAD talib;

WITH SALDOS_CONTA (ID_CLIENTE, DATA_REFERENCIA, SALDO) AS (
    VALUES
        (101, DATE '2026-08-31', 1000.0),
        (101, DATE '2026-09-30', 1200.0),
        (101, DATE '2026-10-31', 1400.0),
        (101, DATE '2026-11-30', 1600.0)
)
SELECT
    ID_CLIENTE,
    t_sma(list(SALDO::DOUBLE ORDER BY DATA_REFERENCIA), 3) AS MEDIA_MOVEL_3
FROM SALDOS_CONTA
GROUP BY ID_CLIENTE;
```

As funções `t_*` recebem listas ordenadas; as funções `ta_*` admitem agregação
e janelas. A média móvel exige três observações no exemplo. Para atributos de
modelos preditivos, limite a série à data de corte e preserve a periodicidade.

Fonte do desenvolvedor · [neuesql/atm_talib](https://github.com/neuesql/atm_talib) ·
[Referência de funções](https://github.com/neuesql/atm_talib/blob/main/index.md).

## Geografia da rede bancária

### `spatial` · cobertura territorial de agências

Processa geometrias e relações espaciais. O exemplo identifica quais agências
sintéticas estão dentro de um perímetro ilustrativo. As coordenadas dos pontos e
do polígono seguem a mesma ordem, longitude e latitude.

```sql
INSTALL spatial FROM core;
LOAD spatial;

WITH agencias(id, longitude, latitude) AS (
    VALUES (1, -51.23, -30.03), (2, -51.12, -29.90)
),
perimetro AS (
    SELECT ST_GeomFromText(
        'POLYGON ((-51.30 -30.10, -51.15 -30.10, -51.15 -29.95,
                   -51.30 -29.95, -51.30 -30.10))'
    ) AS geometria
)
SELECT id
FROM agencias CROSS JOIN perimetro
WHERE ST_Within(ST_Point(longitude, latitude), geometria);
```

Fonte do desenvolvedor · [DuckDB, funções espaciais](https://duckdb.org/docs/2.0/core_extensions/spatial/functions) ·
[DuckDB Spatial no GitHub](https://github.com/duckdb/duckdb-spatial).

### `a5` · agregação territorial de transações

Converte longitude e latitude em identificadores de células geoespaciais
hierárquicas. Em dados sintéticos de cartões, o exemplo agrega o volume por
célula na resolução 12.

```sql
INSTALL a5 FROM query_farm;
LOAD a5 FROM query_farm;

WITH compras(longitude, latitude, valor) AS (
    VALUES (-51.23, -30.03, 100.00), (-51.23, -30.03, 50.00), (-51.12, -29.90, 80.00)
)
SELECT
    a5_lonlat_to_cell(longitude, latitude, 12) AS celula,
    count(*) AS transacoes,
    sum(valor) AS volume
FROM compras
GROUP BY celula;
```

Fonte do desenvolvedor · [Query.Farm, A5 para DuckDB 2.0](https://query.farm/blog/a5-for-duckdb-2/) ·
[Query-farm/a5](https://github.com/Query-farm/a5).

## Busca e análise de atendimento

### `fts` · localização de reclamações

Cria índices textuais e classifica documentos pela relevância BM25. O exemplo
busca reclamações sintéticas sobre tarifas, com stemmer para português.

```sql
INSTALL fts FROM core;
LOAD fts;

CREATE TABLE reclamacoes_fts (id INTEGER PRIMARY KEY, relato VARCHAR);
INSERT INTO reclamacoes_fts VALUES
    (1, 'Cliente contesta tarifa de manutenção da conta.'),
    (2, 'Cartão bloqueado após erro de senha.');

PRAGMA create_fts_index(
    'reclamacoes_fts', 'id', 'relato', stemmer = 'portuguese', stopwords = 'none'
);

WITH busca AS (
    SELECT
        id,
        relato,
        fts_main_reclamacoes_fts.match_bm25(id, 'tarifa') AS relevancia
    FROM reclamacoes_fts
)
SELECT id, relato, relevancia
FROM busca
WHERE relevancia IS NOT NULL
ORDER BY relevancia DESC;
```

Fonte do desenvolvedor · [DuckDB, busca textual](https://duckdb.org/docs/2.0/core_extensions/full_text_search).

### `open_prompt` · triagem de relatos sintéticos

Envia prompts SQL a uma API compatível com Chat Completions. Configure o
endpoint e a autenticação de um modelo local ou de homologação conforme o
mantenedor. O exemplo envia apenas um relato sintético e pede uma categoria para
triagem assistida.

```sql
INSTALL open_prompt FROM query_farm;
LOAD open_prompt FROM query_farm;

WITH atendimento(id, relato) AS (
    VALUES (1, 'O aplicativo mostrou dois débitos para a mesma compra.')
)
SELECT
    id,
    open_prompt(
        relato,
        system_prompt := 'Responda somente com CARTAO, PIX, TARIFA ou OUTRO.',
        temperature := 0.0,
        max_tokens := 12
    ) AS categoria_sugerida
FROM atendimento;
```

Fonte do desenvolvedor · [Query.Farm, Open Prompt para DuckDB 2.0](https://query.farm/blog/openprompt-for-duckdb-2/) ·
[Query-farm/openprompt](https://github.com/Query-farm/openprompt).

