# Extensões locais para DuckDB 2.0.0

Pacote para Linux x86-64. Inclui `dash`, `decimal_arithmetic`, `duck_lineage`, `ggsql`, `pivot_table` e `toml`. As revisões upstream e as adaptações C++ estão em `sources.tsv` e `patches/`.

## Instalação no R

Extraia `duckdb-local-v2.0.0-linux_amd64.tar.gz` em um diretório permanente. Execute `install.R` no diretório extraído, na sessão em que `DuckdbConnection()` está disponível. O script usa o repositório local `sabby_local`. O arquivo `public.pem` e o manifesto em `.well-known/` contêm a chave usada na verificação das extensões.

Nas próximas sessões, carregue as extensões desejadas com `LOAD nome FROM sabby_local`. `INSTALL AND LOAD` é necessário na primeira instalação. Para verificar a carga, consulte `SELECT extension_name, loaded FROM duckdb_extensions() WHERE loaded`.

O pacote usa a API C++ do DuckDB `v2.0.0`, revisão `d54cbbe3df`. Confira `PRAGMA version` na conexão do R e `PRAGMA platform` para confirmar `linux_amd64`. O fluxo de publicação usa GCC e ligação estática com o DuckDB. A instalação funciona a partir do pacote extraído, inclusive sem acesso à internet.

O teste SQL `smoke.sql` deve ser executado em uma conexão de teste após carregar as extensões. Ele cria tabelas de teste e o enum de configuração usado pelo `pivot_table`.
