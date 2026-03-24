# wgc-download

CLI tool to list, download, and selectively extract game files from the Wargaming Game Center (WGC) CDN.

Supports all games available through WGC: **World of Tanks**, **World of Warships**, **WoT Blitz**, **World of Warplanes**, and others.

The key feature is **remote partial extraction** — you can pull individual files out of a 58 GB archive by downloading only the bytes you need, using HTTP range requests against the CDN.

## How it works

Wargaming distributes updates as `.dspkg` archives (7z format) split into *parts*: `client`, `locale`, `sdcontent`, `hotfix`. Each part contains one archive.

This tool:

1. Queries the WGC showroom API to discover all available games and their update servers
2. Fetches version metadata and patch chains for the selected game
3. Parses 7z archive headers remotely via HTTP range requests (~512 KB to index any archive)
4. Fetches only the compressed streams for files you request
5. Decompresses locally (LZMA2, BCJ+LZMA2)

## Install

```
pip install .
```

Or run directly:

```
python wgc.py <command>
```

Requires Python 3.10+ and [py7zr](https://pypi.org/project/py7zr/) (installed automatically).

## Usage

### List available games

```bash
wgc-download games
```

```
Available games:

  WOT.EU.PRODUCTION         World of Tanks            Europe
  WOT.NA.PRODUCTION         World of Tanks            North America
  WOT.ASIA.PRODUCTION       World of Tanks            Asia
  WOWS.WW.PRODUCTION        World of Warships         World of Warships
  WOWS.PT.PRODUCTION        World of Warships         World of Warships Public Test
  WOTB.WW.PRODUCTION        WoT Blitz                 Worldwide
  WOWP.WW.PRODUCTION        World of Warplanes        Worldwide
  HEAT.WW.PRODUCTION        Heat                      None
```

### List versions and parts

```bash
wgc-download list WOWS.WW.PRODUCTION
wgc-download list WOT.EU.PRODUCTION
wgc-download list WOT.EU.PRODUCTION --files client
```

### Download a full .dspkg

```bash
wgc-download download WOWS.WW.PRODUCTION locale --all -d downloads/
```

Skips files that are already downloaded with the correct size. Uses atomic writes (`.part` + rename).

### Extract files from a remote archive (no full download)

List and extract individual files from a remote `.dspkg` without downloading the entire archive:

```bash
# List all files inside the client archive
wgc-download extract WOWS.WW.PRODUCTION client --list

# Extract a single file
wgc-download extract WOWS.WW.PRODUCTION client WorldOfWarships.exe -d out/

# Extract files matching a glob
wgc-download extract WOWS.WW.PRODUCTION locale --filter "*/res/texts/en/**" -d out/

# Works with any game
wgc-download extract WOT.EU.PRODUCTION client --list
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
