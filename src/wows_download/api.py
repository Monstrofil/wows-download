"""WGC API client — metadata and patches chain fetching."""

import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API_BASE = "https://wgus-eu.wargaming.net/api/v1"
GUID = "WOWS.WW.PRODUCTION"
CHAIN_BOOTSTRAP = "f00"
META_PROTO = "7.10"
PATCHES_PROTO = "1.11"
CLIENT_TYPE = "high"
LANG_CODE = "EN"
GC_PUBLISHER = "wargaming"

USER_AGENT = "wows-download/0.1.0"


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_metadata() -> ET.Element:
    url = (
        f"{API_BASE}/metadata/"
        f"?guid={GUID}&chain_id={CHAIN_BOOTSTRAP}&protocol_version={META_PROTO}"
    )
    return ET.fromstring(fetch_url(url))


def fetch_patches_chain(metadata_version: str, chain_id: str) -> ET.Element:
    params = urllib.parse.urlencode({
        "game_id": GUID,
        "protocol_version": PATCHES_PROTO,
        "metadata_version": metadata_version,
        "metadata_protocol_version": META_PROTO,
        "client_type": CLIENT_TYPE,
        "lang": LANG_CODE,
        "chain_id": chain_id,
        "game_installation": "false",
        "gc_publisher": GC_PUBLISHER,
        "client_current_version": "0",
        "hotfix_current_version": "0",
        "locale_current_version": "0",
        "sdcontent_current_version": "0",
    })
    url = f"{API_BASE}/patches_chain/?{params}"
    return ET.fromstring(fetch_url(url))


def build_direct_url(torrent_url: str, file_name: str) -> str | None:
    if not torrent_url or not file_name:
        return None
    p = urllib.parse.urlparse(torrent_url)
    segs = [s for s in p.path.split("/") if s]
    if not segs:
        return None
    segs[-1] = os.path.basename(file_name)
    new_path = "/" + "/".join(segs)
    return urllib.parse.urlunparse((p.scheme, p.netloc, new_path, p.params, p.query, p.fragment))


def parse_patches(patches_root: ET.Element) -> dict:
    patches = {}
    latest_version = None

    for patch in patches_root.findall("./patches_chain/patch"):
        part = (patch.findtext("part") or "").strip()
        version_from = (patch.findtext("version_from") or "").strip()
        version_to = (patch.findtext("version_to") or "").strip()

        if version_to and latest_version is None:
            latest_version = version_to

        torrent_urls = [
            u.text.strip()
            for u in patch.findall("./torrent/urls/url")
            if u.text and u.text.strip()
        ]

        files = []
        for f in patch.findall("./files/file"):
            name = (f.findtext("name") or "").strip()
            size = int((f.findtext("size") or "0").strip() or 0)
            unpacked = int((f.findtext("unpacked_size") or "0").strip() or 0)
            files.append({
                "name": name,
                "basename": os.path.basename(name),
                "size": size,
                "unpackedSize": unpacked,
                "downloadUrl": build_direct_url(torrent_urls[0] if torrent_urls else "", name),
            })

        patches[part] = {
            "part": part,
            "versionFrom": version_from,
            "versionTo": version_to,
            "files": files,
        }

    return {"latestVersion": latest_version, "patches": patches}


def get_manifest() -> dict:
    """Fetch metadata + patches_chain and return parsed manifest."""
    meta = fetch_metadata()
    metadata_version = (meta.findtext("version") or "").strip()
    chain_id = (meta.findtext("./predefined_section/chain_id") or "").strip()

    if not metadata_version or not chain_id:
        raise RuntimeError("Could not parse metadata (version or chain_id missing)")

    patches_root = fetch_patches_chain(metadata_version, chain_id)
    manifest = parse_patches(patches_root)
    manifest["metadataVersion"] = metadata_version
    manifest["chainId"] = chain_id
    return manifest
