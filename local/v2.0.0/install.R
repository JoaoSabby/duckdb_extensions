# Execute este arquivo no diretório extraído com uma conexão DuckDB já aberta.
# Use o nome da conexão em uso pelo projeto.
library(DBI)
con <- DuckdbConnection()

# Mantém o espelho principal e o repositório local em registros distintos.
repo <- dbQuoteString(con, normalizePath(getwd(), mustWork = TRUE))
stopifnot(file.exists(file.path(getwd(), ".well-known", "duckdb-extension-repo.json")))
invisible(dbExecute(con, "SET allow_extension_repositories = 'allowed'"))
invisible(dbExecute(con, paste(
  "CREATE EXTENSION REPOSITORY IF NOT EXISTS sabby_local WITH PREFIX", repo
)))

# Instala a partir da cópia local e carrega explicitamente do mesmo repositório.
extensions <- c("dash", "decimal_arithmetic", "duck_lineage", "ggsql", "pivot_table", "toml")
for(extension in extensions){
  invisible(dbExecute(con, paste("INSTALL AND LOAD", extension, "FROM sabby_local")))
}
