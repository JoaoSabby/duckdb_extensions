"""Synchronize DuckDB binaries from their published repositories."""

import json
import os
import re
import shutil
import subprocess
from collections import Counter
from hashlib import file_digest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory


CORE_DOCS = "https://raw.githubusercontent.com/duckdb/duckdb-web/main/docs"
COMMUNITY_TREE = (
    "https://api.github.com/repos/duckdb/community-extensions"
    "/git/trees/main?recursive=1"
)
REPOSITORIES = {
    "core": "https://extensions.duckdb.org",
    "community": "https://community-extensions.duckdb.org",
    "query_farm": "https://duckdb-extensions.query.farm",
    "neuesql": "https://neuesql.github.io/atm_talib",
}
KEY_PATH = Path(".well-known/duckdb-extension-repo.json")
RELEASE_ASSET_LIMIT = 2 * 1024**3 - 1
EXTENSION_NAME = r"[a-z0-9_-]+"


def download(url, destination, *, headers=(), max_bytes=RELEASE_ASSET_LIMIT):
    # Restrict redirects to HTTPS and keep error responses out of the mirror
    command = [
        "curl", "--silent", "--show-error", "--fail", "--location",
        "--proto", "=https", "--proto-redir", "=https", "--retry", "3",
        "--connect-timeout", "15", "--max-time", "600",
        "--max-filesize", str(max_bytes), "--output", str(destination),
        "--write-out", "%{http_code}",
    ]
    for header in headers:
        command.extend(["--header", header])

    return subprocess.run([*command, url], capture_output=True, text=True, check=False)


def fetch_required(url, destination, **options):
    result = download(url, destination, **options)
    if result.returncode:
        raise RuntimeError(f"{url}: {result.stderr.strip()}")


def discover(version, staging):
    # Restrict synchronization to the explicitly configured extensions
    origins = {}
    for origin in REPOSITORIES:
        for name in os.environ.get(f"{origin.upper()}_EXTENSIONS", "").split():
            if not re.fullmatch(EXTENSION_NAME, name):
                raise ValueError(f"Invalid extension name: {name}")
            origins[name] = origin
    return origins


def fetch_extension(name, origin, version, platform, staging):
    relative = Path(version, platform, f"{name}.duckdb_extension.gz")
    url = f"{REPOSITORIES[origin]}/{relative.as_posix()}"

    # Keep third-party binaries separate from the official signing authorities
    if origin in {"query_farm", "neuesql"}:
        relative = Path(origin) / relative

    temporary = staging / relative
    temporary.parent.mkdir(parents=True, exist_ok=True)
    result = download(url, temporary)

    if result.returncode == 22 and result.stdout == "404":
        return "unavailable", relative, 0, url

    if result.returncode == 63:
        return "failed", relative, 0, f"{url} (exceeds the GitHub Releases asset limit)"

    if result.returncode:
        return "failed", relative, 0, f"{url} ({result.stderr.strip()})"

    # Validate the entire gzip stream, including its checksum and end marker
    validation = subprocess.run(
        ["gzip", "-t", str(temporary)], capture_output=True, text=True, check=False
    )
    if validation.returncode:
        return "failed", relative, 0, f"{url} ({validation.stderr.strip()})"

    return "validated", relative, temporary.stat().st_size, url


def write_report(results):
    counts = Counter(status for status, *_ in results)
    total_bytes = sum(size for _, _, size, _ in results)

    for status, _, size, detail in results:
        print(f"{status:18} {size:>10} {detail}", flush=True)

    summary = (
        f"Validated: {counts['validated']} | Unavailable: {counts['unavailable']} | "
        f"Failed: {counts['failed']} | "
        f"Total validated: {total_bytes / 1024**2:.1f} MiB"
    )
    print(summary, flush=True)

    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary_path).open("a", encoding="utf-8") as report:
            report.write(f"{summary}\n\n")
            for status, relative, _, detail in results:
                if status != "validated":
                    report.write(f"- {status}: [{relative.name}]({detail.split(' ')[0]})\n")


def run_gh(*arguments):
    result = subprocess.run(
        ["gh", *arguments], text=True, stdout=subprocess.PIPE, check=True
    )
    return result.stdout


def publish_release(tag, title, assets):
    repository = os.environ["GITHUB_REPOSITORY"]

    # Query all existing assets, since releases can hold over 100 binaries
    release = subprocess.run(
        ["gh", "api", f"repos/{repository}/releases/tags/{tag}", "--include"],
        capture_output=True, text=True, check=False,
    )
    if release.returncode:
        status = release.stdout.splitlines()[0] if release.stdout else ""
        if not re.match(r"HTTP/\S+ 404(?: |$)", status):
            raise RuntimeError(release.stderr.strip() or f"Could not read release {tag}")

        run_gh(
            "release", "create", tag, "--target", os.environ["GITHUB_SHA"],
            "--title", title, "--notes", "Validated DuckDB extension binaries.",
            "--latest=false",
        )
        release_id = json.loads(run_gh("api", f"repos/{repository}/releases/tags/{tag}"))["id"]
    else:
        _, _, body = release.stdout.partition("\n\n")
        release_id = json.loads(body)["id"]

    current = run_gh(
        "api", "--paginate", f"repos/{repository}/releases/{release_id}/assets?per_page=100",
        "--jq", '.[] | [.name, (.digest // "")] | @tsv',
    )
    digests = dict(row.split("\t", 1) for row in current.splitlines())

    # Replace a release asset only when its bytes have changed
    changed = []
    for path in assets:
        with path.open("rb") as source:
            digest = f"sha256:{file_digest(source, 'sha256').hexdigest()}"
        if digests.get(path.name) != digest:
            changed.append(str(path))

    for start in range(0, len(changed), 20):
        run_gh("release", "upload", tag, "--clobber", *changed[start:start + 20])

    print(f"{tag}: {len(changed)} asset(s) uploaded", flush=True)


def main():
    version = os.environ["DUCKDB_VERSION"]
    platform = os.environ["PLATFORM"]

    with TemporaryDirectory(prefix="duckdb-mirror-") as temporary_dir:
        staging = Path(temporary_dir)
        origins = discover(version, staging)
        print(f"Candidates by origin: {dict(Counter(origins.values()))}", flush=True)

        # Await discovery and validation for all origins before changing files
        with ThreadPoolExecutor(max_workers=12) as executor:
            requests = [
                executor.submit(fetch_extension, name, origin, version, platform, staging)
                for name, origin in sorted(origins.items())
            ]
            results = [request.result() for request in requests]

        write_report(results)
        if any(status == "failed" for status, *_ in results):
            raise SystemExit("Extension download or validation failed")

        if "query_farm" in origins.values():
            # Publish the upstream discovery document for signature verification
            key_file = staging / "query_farm" / KEY_PATH
            key_file.parent.mkdir(parents=True, exist_ok=True)
            fetch_required(
                f"{REPOSITORIES['query_farm']}/{KEY_PATH.as_posix()}",
                key_file,
                max_bytes=64 * 1024,
            )
            keys = json.loads(key_file.read_text(encoding="utf-8"))["signature_keys"]
            if not isinstance(keys, list) or not keys or not all(isinstance(key, str) for key in keys):
                raise RuntimeError("Query.Farm did not publish valid repository key metadata")

        if os.environ.get("PUBLISH") != "true":
            return

        # Use separate releases so clients can identify the signing authority
        official_assets = []
        query_farm_assets = []
        neuesql_assets = []
        for status, relative, _, _ in results:
            if status != "validated":
                continue
            if relative.parts[0] == "query_farm":
                query_farm_assets.append(staging / relative)
            elif relative.parts[0] == "neuesql":
                neuesql_assets.append(staging / relative)
            else:
                official_assets.append(staging / relative)

        if official_assets:
            publish_release(
                f"extensions-{version}-{platform}",
                f"DuckDB {version} extensions ({platform})",
                official_assets,
            )
        if query_farm_assets:
            publish_release(
                f"query-farm-{version}-{platform}",
                f"Query.Farm extensions for DuckDB {version} ({platform})",
                [*query_farm_assets, key_file],
            )

        # NeueSQL publishes unsigned binaries; do not mix them with signed assets
        if neuesql_assets:
            publish_release(
                f"neuesql-{version}-{platform}",
                f"NeueSQL unsigned extensions for DuckDB {version} ({platform})",
                neuesql_assets,
            )

        # Keep the existing raw GitHub URLs current for yaml and dq
        for source in official_assets:
            if source.name in {"yaml.duckdb_extension.gz", "dq.duckdb_extension.gz"}:
                destination = source.relative_to(staging)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)


if __name__ == "__main__":
    main()

