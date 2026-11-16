# DuckDB extension mirror

The GitHub Actions workflow discovers Core and Community extensions and checks for
Linux x86-64 binaries for DuckDB v2.0.0. The YAML also lists the signed Query.Farm
extensions to mirror. Each run reports unavailable downloads and validates gzip
integrity before publishing any assets.

The workflow runs on Sunday at 03:00 UTC. A manual run validates the mirror by default.
Select **publish** in **Actions → Sync DuckDB Extensions → Run workflow** to publish
from the default branch.

## Install from the mirror

Core and Community binaries are available from the
[DuckDB extensions release](https://github.com/JoaoSabby/duckdb_extensions/releases/tag/extensions-v2.0.0-linux_amd64)
after the first publishing run. Install a binary through its asset URL.

```sql
INSTALL 'https://github.com/JoaoSabby/duckdb_extensions/releases/download/extensions-v2.0.0-linux_amd64/json.duckdb_extension.gz';
LOAD json;
```

The [Query.Farm release](https://github.com/JoaoSabby/duckdb_extensions/releases/tag/query-farm-v2.0.0-linux_amd64)
contains the upstream signed assets and the public key document. To use it as a local
DuckDB repository, save that document as `.well-known/duckdb-extension-repo.json`
under a local directory and copy the gzip files into its `v2.0.0/linux_amd64/`
subdirectory. Register the local directory as a named DuckDB extension repository
with the verified Query.Farm signing keys, then install and load from that name.
See the [DuckDB extension repository documentation](https://duckdb.org/docs/2.0/extensions/extension_repositories).
