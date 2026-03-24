# wows-download

CLI tool to list, download, and selectively extract World of Warships game files from the Wargaming Game Center (WGC) CDN.

The key feature is **remote partial extraction** — you can pull individual files out of a 58 GB archive by downloading only the bytes you need, using HTTP range requests against the CDN.

## How it works

WoWS distributes updates as `.dspkg` archives (7z format) split into *parts*: `client`, `locale`, `sdcontent`, `hotfix`. Each part contains one archive.

This tool:

1. Queries the WGC API to discover available versions and download URLs
2. Parses 7z archive headers remotely via HTTP range requests (~512 KB to index any archive regardless of size)
3. Fetches only the compressed streams for files you request
4. Decompresses locally (LZMA2, BCJ+LZMA2)

| Archive | Full size | Index cost |
|---------|-----------|------------|
| locale | 67 MB | 512 KB |
| sdcontent | 19.3 GB | 512 KB |
| client | 58.7 GB | 512 KB |

## Install

```
pip install .
```

Or run directly:

```
python wows.py <command>
```

Requires Python 3.10+ and [py7zr](https://pypi.org/project/py7zr/) (installed automatically).

## Usage

### List available versions and parts

```bash
# Overview — latest version, all parts with sizes
wows-download list

# Files in a specific part
wows-download list --files locale
```

```
Game:              WOWS.WW.PRODUCTION
Latest version:    15.2.0.0.12116141

Parts (4):

  client                 1 file(s)      58.7 GB
  locale                 1 file(s)      66.9 MB
  sdcontent              1 file(s)      19.3 GB
  hotfix                 1 file(s)        181 B
```

### Download a full .dspkg

```bash
# Download a specific file
wows-download download locale wows.ww_15.2.0.0.12116141_locale.dspkg

# Download all files in a part
wows-download download locale --all -d downloads/
```

Skips files that are already downloaded with the correct size. Uses atomic writes (`.part` + rename).

### Extract files from a remote archive (no full download)

This is where it gets interesting. You can list and extract individual files from a remote `.dspkg` without downloading the entire archive:

```bash
# List all files inside the 58.7 GB client archive
wows-download extract client --list

# Extract a single file
wows-download extract client WorldOfWarships.exe -d out/

# Extract files matching a glob
wows-download extract locale --filter "*/res/texts/en/**" -d out/

# Extract system_data.idx (31 KB from a 58.7 GB archive)
wows-download extract client "bin/12116141/idx/system_data.idx" -d out/

# Extract all DLLs
wows-download extract client --filter "*.dll" -d out/
```

Example output:

```
Archive: wows.ww_15.2.0.0.12116141_client.dspkg (58.7 GB)
Reading archive index via range requests...
Index: 935 files (2 HTTP requests, ~512KB transferred)

Extracting 1 file(s): 12.9 KB to download, 31.4 KB uncompressed

  GET  bin/12116141/idx/system_data.idx (12.9 KB) ... -> 31.4 KB

Done: 1 file(s) extracted
Total HTTP requests: 3
```

3 HTTP requests to pull a 31 KB file from a 58.7 GB archive.

## How remote extraction works

`.dspkg` files are 7z archives with non-solid compression (each file is independently compressed). This makes selective extraction possible:

1. **HEAD request** — get file size and confirm range request support
2. **Range request #1** — fetch the 7z signature header (32 bytes) to locate the metadata
3. **Range request #2** — fetch the metadata/index from the end of the file (~256 KB)
4. **Parse the index** — py7zr decodes the 7z header to get file names, byte offsets, and compression info
5. **Range request per file** — fetch only the compressed bytes for each requested file
6. **Decompress locally** — LZMA2 or BCJ+LZMA2 depending on content type

## License

MIT
