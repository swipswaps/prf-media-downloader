#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRF Media Downloader — v2025.08.22

Sources: Unsplash, Pexels, Pixabay (official APIs), Coverr, Mixkit, Videvo (public catalog pages)
Features:
  • GUI & CLI
  • Multi-threaded downloads with robust retries/timeouts
  • Source selection
  • Set items-per-source & output folder
  • Thumbnail preview/selection (images & videos where available)
  • Organized folders: images/, videos/ per source
  • Manifest JSON + log file
  • API keys via env (.env supported) or CLI flags
  • Idempotent (skips existing files by content hash filename)
  • Clear user messages (PRF)

Licensing note:
  • Unsplash, Pexels, Pixabay: use official APIs under their licenses.
  • Coverr & Mixkit: free use per their site licenses (verify per clip).
  • Videvo: licensing varies per asset; verify the license on each item before commercial use.
  • Always inspect each asset’s license at time of download.

Tested: Python 3.9+ (Linux/macOS/Windows)
"""

from __future__ import annotations
import os
import sys
import re
import io
import json
import time
import math
import hashlib
import queue
import shutil
import signal
import threading
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Networking
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Optional GUI / images
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    GUI_AVAILABLE = True
except Exception:
    GUI_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# HTML parse
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except Exception:
    BS4_AVAILABLE = False

# .env (optional)
def load_dotenv_if_present():
    dotenv = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(dotenv):
        try:
            with open(dotenv, "r", encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k,v = line.split("=",1)
                    if k and (k not in os.environ):
                        os.environ[k.strip()]=v.strip()
        except Exception:
            pass

load_dotenv_if_present()

APP_NAME = "PRF Media Downloader"
DEFAULT_OUT = os.path.abspath("downloads")
DEFAULT_ITEMS = 10
DEFAULT_THREADS = min(8, max(2, os.cpu_count() or 4))
USER_AGENT = f"{APP_NAME}/1.0 (+https://example.local) requests"

LOG_DIR = os.path.abspath(".prf_media_logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "prf_media_downloader.log")

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ---- Requests session with retry/timeouts
def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=100)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return s

SESSION = make_session()

def safe_filename(text: str, ext: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")
    if not base:
        base = "asset"
    if not ext.startswith("."):
        ext = "." + ext
    return f"{base}{ext}"

def sha1_of_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()

def ensure_dirs(base: str) -> Dict[str, str]:
    sub = {
        "images": os.path.join(base, "images"),
        "videos": os.path.join(base, "videos"),
        "meta": os.path.join(base, "_meta"),
    }
    for p in [base] + list(sub.values()):
        os.makedirs(p, exist_ok=True)
    return sub

def write_manifest(base: str, manifest: Dict[str, Any]):
    try:
        ensure_dirs(base)
        mpath = os.path.join(base, "_meta", "manifest.json")
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        log(f"Manifest written: {mpath}")
    except Exception as e:
        log(f"Manifest write failed: {e}")

def download_to_path(url: str, dst_path: str, timeout: int = 25) -> Tuple[bool, Optional[str]]:
    """Download URL → dst_path atomically. Returns (ok, sha1)."""
    try:
        tmp_path = dst_path + ".part"
        digest = hashlib.sha1()
        with SESSION.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    digest.update(chunk)
        
        final_digest = digest.hexdigest()
        # Idempotent filename by hash (avoid duplicates)
        root, ext = os.path.splitext(dst_path)
        final_path = f"{root}-{final_digest[:10]}{ext}"
        
        if os.path.exists(final_path):
            os.remove(tmp_path) # cleanup partial download
            return True, final_digest

        os.replace(tmp_path, final_path)
        return True, final_digest
    except Exception as e:
        log(f"DOWNLOAD FAIL {url} -> {dst_path}: {e}")
        # Clean up partial file if it exists
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False, None

# ---------------- Data shapes
@dataclass
class Asset:
    source: str                      # 'unsplash'|'pexels'|...
    kind: str                        # 'image' or 'video'
    title: str
    preview_url: Optional[str]
    download_url: str
    ext: str                         # .jpg, .mp4, etc.
    license_hint: str
    page_url: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

# ---------------- Source fetchers ----------------

def fetch_unsplash(query: str, count: int, key: Optional[str]) -> List[Asset]:
    assets: List[Asset] = []
    if not key:
        log("Unsplash skipped (no API key).")
        return assets
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {"query": query, "per_page": count}
        headers = {"Authorization": f"Client-ID {key}"}
        r = SESSION.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        for it in data.get("results", []):
            preview = (it.get("urls") or {}).get("small") or (it.get("urls") or {}).get("thumb")
            full = (it.get("urls") or {}).get("full") or (it.get("urls") or {}).get("regular")
            if not full: 
                continue
            assets.append(Asset(
                source="unsplash",
                kind="image",
                title=it.get("alt_description") or f"unsplash-{it.get('id','img')}",
                preview_url=preview,
                download_url=full,
                ext=".jpg",
                license_hint="Unsplash License (free for commercial; see site)",
                page_url=it.get("links", {}).get("html"),
                meta={"author": it.get("user", {}).get("name")}
            ))
    except Exception as e:
        log(f"Unsplash fetch error: {e}")
    return assets

def fetch_pexels(query: str, count: int, key: Optional[str]) -> List[Asset]:
    assets: List[Asset] = []
    if not key:
        log("Pexels skipped (no API key).")
        return assets
    headers = {"Authorization": key}
    try:
        # Images
        r = SESSION.get("https://api.pexels.com/v1/search",
                        params={"query": query, "per_page": count},
                        headers=headers, timeout=20)
        r.raise_for_status()
        for p in r.json().get("photos", []):
            src = p.get("src") or {}
            assets.append(Asset(
                source="pexels",
                kind="image",
                title=p.get("alt") or f"pexels-{p.get('id','img')}",
                preview_url=src.get("small") or src.get("medium"),
                download_url=src.get("original") or src.get("large2x") or src.get("large"),
                ext=".jpg",
                license_hint="Pexels License (free; attribution not required)",
                page_url=p.get("url"),
                meta={"author": (p.get("photographer") or "")}
            ))
        # Videos
        rv = SESSION.get("https://api.pexels.com/videos/search",
                         params={"query": query, "per_page": count},
                         headers=headers, timeout=20)
        rv.raise_for_status()
        for v in rv.json().get("videos", []):
            files = v.get("video_files") or []
            best = sorted(files, key=lambda x: (x.get("quality")=="hd", x.get("width") or 0), reverse=True)
            if not best:
                continue
            dl = best[0].get("link")
            thumb = (v.get("image") or None)
            assets.append(Asset(
                source="pexels",
                kind="video",
                title=f"pexels-{v.get('id','video')}",
                preview_url=thumb,
                download_url=dl,
                ext=".mp4",
                license_hint="Pexels License (free; attribution not required)",
                page_url=v.get("url"),
                meta={"duration": v.get("duration")}
            ))
    except Exception as e:
        log(f"Pexels fetch error: {e}")
    return assets

def fetch_pixabay(query: str, count: int, key: Optional[str]) -> List[Asset]:
    assets: List[Asset] = []
    if not key:
        log("Pixabay skipped (no API key).")
        return assets
    try:
        # Images
        r = SESSION.get("https://pixabay.com/api/",
                        params={"key": key, "q": query, "per_page": count},
                        timeout=20)
        r.raise_for_status()
        for h in r.json().get("hits", []):
            assets.append(Asset(
                source="pixabay",
                kind="image",
                title=f"pixabay-{h.get('id','img')}",
                preview_url=h.get("previewURL"),
                download_url=h.get("largeImageURL") or h.get("webformatURL"),
                ext=".jpg",
                license_hint="Pixabay License (free; see site)",
                page_url=h.get("pageURL"),
                meta={"author": h.get("user")}
            ))
        # Videos
        rv = SESSION.get("https://pixabay.com/api/videos/",
                         params={"key": key, "q": query, "per_page": count},
                         timeout=20)
        rv.raise_for_status()
        for h in rv.json().get("hits", []):
            vids = h.get("videos") or {}
            best = vids.get("large") or vids.get("medium") or vids.get("small")
            if not best:
                continue
            assets.append(Asset(
                source="pixabay",
                kind="video",
                title=f"pixabay-{h.get('id','video')}",
                preview_url=h.get("picture_id") and f"https://i.vimeocdn.com/video/{h.get('picture_id')}_295x166.jpg",
                download_url=best.get("url"),
                ext=".mp4",
                license_hint="Pixabay License (free; see site)",
                page_url=h.get("pageURL"),
                meta={}
            ))
    except Exception as e:
        log(f"Pixabay fetch error: {e}")
    return assets

def bs4_required():
    if not BS4_AVAILABLE:
        raise RuntimeError("BeautifulSoup4 not installed. Re-run installer.")

def fetch_coverr(query: str, count: int) -> List[Asset]:
    """Coverr search page provides <source> or <video> tags on result cards."""
    bs4_required()
    assets: List[Asset] = []
    try:
        url = "https://coverr.co/search"
        r = SESSION.get(url, params={"q": query}, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("video, source")
        seen = set()
        for el in cards:
            src = el.get("src") or el.get("data-src")
            if not src or src in seen:
                continue
            seen.add(src)
            thumb = None
            parent = el.parent
            if parent and hasattr(parent, "get"):
                poster = parent.get("poster") or parent.get("data-poster")
                thumb = poster or thumb
            assets.append(Asset(
                source="coverr",
                kind="video",
                title="coverr-video",
                preview_url=thumb,
                download_url=src,
                ext=".mp4",
                license_hint="Coverr Free License (see site)",
                page_url="https://coverr.co",
                meta={}
            ))
            if len(assets) >= count:
                break
    except Exception as e:
        log(f"Coverr fetch error: {e}")
    return assets

def fetch_mixkit(query: str, count: int) -> List[Asset]:
    """Mixkit category pages vary; try generic free-stock-video search."""
    bs4_required()
    assets: List[Asset] = []
    try:
        # Generic search page
        url = f"https://mixkit.co/search/{requests.utils.quote(query)}/"
        r = SESSION.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.select("a"):
            href = a.get("href") or ""
            if re.match(r"^/free-stock-video/\d+/", href):
                links.append("https://mixkit.co" + href)
        links = list(dict.fromkeys(links))[:count]
        for lk in links:
            pr = SESSION.get(lk, timeout=20)
            pr.raise_for_status()
            psoup = BeautifulSoup(pr.text, "html.parser")
            # Find a download link; class names can change, so scan for anchor with "download"
            dl = None
            for a in psoup.select("a"):
                txt = (a.text or "").strip().lower()
                if "download" in txt and a.get("href"):
                    dl = a.get("href")
                    if dl.startswith("/"):
                        dl = "https://mixkit.co" + dl
                    break
            thumb = None
            img = psoup.find("meta", {"property":"og:image"})
            if img and img.get("content"):
                thumb = img.get("content")
            if dl:
                assets.append(Asset(
                    source="mixkit",
                    kind="video",
                    title="mixkit-video",
                    preview_url=thumb,
                    download_url=dl,
                    ext=".mp4",
                    license_hint="Mixkit License (free; see site)",
                    page_url=lk,
                    meta={}
                ))
    except Exception as e:
        log(f"Mixkit fetch error: {e}")
    return assets[:count]

def fetch_videvo(query: str, count: int) -> List[Asset]:
    """
    Videvo search page parsing (best-effort; site may change).
    Licensing on Videvo varies by item—user must verify per asset before commercial use.
    """
    bs4_required()
    assets: List[Asset] = []
    try:
        url = "https://www.videvo.net/search/"
        r = SESSION.get(url, params={"q": query}, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a[href^='/video/']")
        hrefs = []
        for a in cards:
            href = a.get("href") or ""
            if href and href.startswith("/video/"):
                hrefs.append("https://www.videvo.net" + href)
        hrefs = list(dict.fromkeys(hrefs))[:count]
        for lk in hrefs:
            pr = SESSION.get(lk, timeout=20)
            pr.raise_for_status()
            psoup = BeautifulSoup(pr.text, "html.parser")
            # Look for download button or source file references
            # Fallback: sniff sources inside <video> tags
            vsrc = None
            vid = psoup.find("video")
            if vid:
                src = vid.find("source")
                if src and src.get("src"):
                    vsrc = src.get("src")
                    if vsrc.startswith("/"):
                        vsrc = "https://www.videvo.net" + vsrc
            # Thumbnail
            thumb = None
            og = psoup.find("meta", {"property":"og:image"})
            if og and og.get("content"):
                thumb = og.get("content")
            if vsrc:
                assets.append(Asset(
                    source="videvo",
                    kind="video",
                    title="videvo-video",
                    preview_url=thumb,
                    download_url=vsrc,
                    ext=".mp4",
                    license_hint="Videvo (license varies; check asset page)",
                    page_url=lk,
                    meta={}
                ))
            if len(assets) >= count:
                break
    except Exception as e:
        log(f"Videvo fetch error: {e}")
    return assets

# --------------- Aggregation ---------------

FETCHERS_API = {
    "unsplash": fetch_unsplash,
    "pexels": fetch_pexels,
    "pixabay": fetch_pixabay,
}
FETCHERS_SCRAPE = {
    "coverr": fetch_coverr,
    "mixkit": fetch_mixkit,
    "videvo": fetch_videvo,
}
ALL_SOURCES = list(FETCHERS_API.keys()) + list(FETCHERS_SCRAPE.keys())

def gather_assets(sources: List[str], query: str, count: int,
                  keys: Dict[str, Optional[str]]) -> List[Asset]:
    log(f"Fetching assets: sources={sources}, query={query!r}, per-source={count}")
    assets: List[Asset] = []

    def run_fetch(name: str) -> List[Asset]:
        if name in FETCHERS_API:
            fn = FETCHERS_API[name]
            key = None
            if name == "unsplash":
                key = keys.get("UNSPLASH_KEY")
            elif name == "pexels":
                key = keys.get("PEXELS_KEY")
            elif name == "pixabay":
                key = keys.get("PIXABAY_KEY")
            return fn(query, count, key)
        else:
            fn = FETCHERS_SCRAPE[name]
            return fn(query, count)

    with ThreadPoolExecutor(max_workers=min(len(sources), 6) or 1) as ex:
        futs = {ex.submit(run_fetch, s): s for s in sources}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                part = fut.result() or []
                assets.extend(part)
                log(f"{name}: {len(part)} assets")
            except Exception as e:
                log(f"{name} fetch failed: {e}")
    return assets

# --------------- Download planner ---------------

def ext_for(asset: Asset) -> str:
    if asset.ext:
        return asset.ext
    # fallback by kind
    return ".mp4" if asset.kind == "video" else ".jpg"

def plan_path(base: str, asset: Asset) -> str:
    dirs = ensure_dirs(base)
    sub = "videos" if asset.kind == "video" else "images"
    fn = safe_filename(f"{asset.source}_{asset.title or asset.source}", ext_for(asset))
    return os.path.join(dirs[sub], fn)

def download_assets(base: str, assets: List[Asset], threads: int = DEFAULT_THREADS) -> List[Dict[str, Any]]:
    ensure_dirs(base)
    results: List[Dict[str, Any]] = []

    def one(a: Asset) -> Dict[str, Any]:
        path = plan_path(base, a)
        ok, digest = download_to_path(a.download_url, path)
        return {
            "ok": ok,
            "path": path,
            "sha1": digest,
            "source": a.source,
            "kind": a.kind,
            "page_url": a.page_url,
            "license_hint": a.license_hint,
            "title": a.title
        }

    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = [ex.submit(one, a) for a in assets]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as e:
                log(f"Download task error: {e}")
    return results

# --------------- GUI ----------------

class SettingsGUI:
    def __init__(self, root, args):
        self.root = root
        self.args = args
        self.root.title(f"{APP_NAME} - Settings")

        # Frame for settings
        frame = ttk.Frame(root, padding="10")
        frame.pack(fill="both", expand=True)

        # Query
        ttk.Label(frame, text="Search Query:").grid(row=0, column=0, sticky="w", pady=2)
        self.query_var = tk.StringVar(value=args.query)
        ttk.Entry(frame, textvariable=self.query_var, width=50).grid(row=0, column=1, columnspan=2, sticky="ew")

        # Items
        ttk.Label(frame, text="Items per Source:").grid(row=1, column=0, sticky="w", pady=2)
        self.items_var = tk.IntVar(value=args.items)
        ttk.Entry(frame, textvariable=self.items_var, width=10).grid(row=1, column=1, sticky="w")

        # Output Directory
        ttk.Label(frame, text="Output Directory:").grid(row=2, column=0, sticky="w", pady=2)
        self.outdir_var = tk.StringVar(value=os.path.abspath(args.outdir))
        out_entry = ttk.Entry(frame, textvariable=self.outdir_var, width=50)
        out_entry.grid(row=2, column=1, columnspan=2, sticky="ew")
        ttk.Button(frame, text="Browse...", command=self.browse_outdir).grid(row=2, column=3, padx=5)

        # Sources
        ttk.Label(frame, text="Sources:").grid(row=3, column=0, sticky="nw", pady=5)
        self.source_vars = {}
        initial_sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
        
        sources_frame = ttk.Frame(frame)
        sources_frame.grid(row=3, column=1, columnspan=3, sticky="w")
        
        # Two columns for sources
        midpoint = (len(ALL_SOURCES) + 1) // 2
        for i, source in enumerate(ALL_SOURCES):
            var = tk.BooleanVar(value=(source in initial_sources))
            self.source_vars[source] = var
            row = i % midpoint
            col = (i // midpoint) * 2
            ttk.Checkbutton(sources_frame, text=source.title(), variable=var).grid(row=row, column=col, sticky="w", padx=5)

        # Start button
        start_btn = ttk.Button(frame, text="Fetch Media", command=self.start_fetching)
        start_btn.grid(row=4, column=1, columnspan=2, pady=20)

    def browse_outdir(self):
        dir_path = filedialog.askdirectory(initialdir=self.outdir_var.get())
        if dir_path:
            self.outdir_var.set(os.path.abspath(dir_path))

    def start_fetching(self):
        # Gather settings from GUI
        self.args.query = self.query_var.get()
        self.args.items = self.items_var.get()
        self.args.outdir = self.outdir_var.get()
        
        selected_sources = [s for s, v in self.source_vars.items() if v.get()]
        if not selected_sources:
            messagebox.showwarning("No Sources", "Please select at least one source.")
            return

        self.args.sources = ",".join(selected_sources)

        # Hide settings and run main logic
        self.root.withdraw()
        run_app_logic(self.args)
        self.root.destroy()

class PreviewGUI:
    def __init__(self, root, assets: List[Asset], outdir: str, threads: int):
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow not installed; preview GUI requires pillow.")
        self.root = root
        self.assets = assets
        self.outdir = outdir
        self.threads = threads
        self.root.title(APP_NAME)
        self.selected = [tk.BooleanVar(value=True) for _ in assets]
        self.img_cache: List[Optional[ImageTk.PhotoImage]] = [None]*len(assets)

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text=f"Preview & Select ({len(assets)} assets)").pack(side="left")
        self.info = ttk.Label(top, text=f"Output: {outdir}")
        self.info.pack(side="right")

        self.canvas = tk.Canvas(root, borderwidth=0)
        self.frame = ttk.Frame(self.canvas)
        self.scroll = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)

        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0,0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        btns = ttk.Frame(root, padding=8)
        btns.pack(fill="x")
        ttk.Button(btns, text="Select All", command=self.select_all).pack(side="left")
        ttk.Button(btns, text="Select None", command=self.select_none).pack(side="left", padx=6)
        ttk.Button(btns, text="Download Selected", command=self.download_selected).pack(side="right")

        self.build_grid()

    def select_all(self):
        for v in self.selected: v.set(True)

    def select_none(self):
        for v in self.selected: v.set(False)

    def build_grid(self, cols: int = 4):
        for i, a in enumerate(self.assets):
            cell = ttk.Frame(self.frame, padding=6, relief="ridge")
            r = i // cols
            c = i % cols
            cell.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            # Title
            ttl = (a.title or f"{a.source} {a.kind}")[:40]
            ttk.Label(cell, text=f"[{a.source}] {ttl}").pack(anchor="w")
            # Thumbnail
            img_lbl = ttk.Label(cell)
            img_lbl.pack()
            # Checkbox
            ttk.Checkbutton(cell, text=f"{a.kind}", variable=self.selected[i]).pack(anchor="w")

            # load thumb async
            def load_thumb(idx=i, lbl=img_lbl, asset=a):
                try:
                    url = asset.preview_url or asset.download_url
                    with SESSION.get(url, timeout=15) as r:
                        r.raise_for_status()
                        im = Image.open(io.BytesIO(r.content))
                        im.thumbnail((260, 160))
                        tkimg = ImageTk.PhotoImage(im)
                        self.img_cache[idx] = tkimg
                        lbl.configure(image=tkimg)
                except Exception:
                    pass
            threading.Thread(target=load_thumb, daemon=True).start()

    def download_selected(self):
        chosen = [a for a, v in zip(self.assets, self.selected) if v.get()]
        if not chosen:
            messagebox.showwarning("No selection", "Please select at least one asset.")
            return
        self.root.withdraw()
        log(f"GUI: downloading {len(chosen)} selected assets...")
        results = download_assets(self.outdir, chosen, threads=self.threads)
        manifest = {"generated_at": time.time(), "results": results}
        write_manifest(self.outdir, manifest)
        messagebox.showinfo("Done", f"Downloaded {sum(1 for r in results if r.get('ok'))} assets.\nSaved to: {self.outdir}")
        self.root.destroy()

# --------------- App Logic & CLI ---------------

def run_app_logic(args):
    """The core logic of fetching and downloading, callable from GUI or CLI."""
    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)

    keys = {
        "UNSPLASH_KEY": os.getenv("UNSPLASH_KEY"),
        "PEXELS_KEY": os.getenv("PEXELS_KEY"),
        "PIXABAY_KEY": os.getenv("PIXABAY_KEY"),
    }
    if getattr(args, 'unsplash_key', None): keys["UNSPLASH_KEY"] = args.unsplash_key
    if getattr(args, 'pexels_key', None):   keys["PEXELS_KEY"]   = args.pexels_key
    if getattr(args, 'pixabay_key', None):  keys["PIXABAY_KEY"]  = args.pixabay_key

    srcs = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    srcs = [s for s in srcs if s in ALL_SOURCES]
    if getattr(args, 'no_scrape', False):
        srcs = [s for s in srcs if s in FETCHERS_API]
    
    if not srcs:
        log("No valid sources selected. Exiting.")
        if GUI_AVAILABLE and args.gui:
            messagebox.showerror("Error", "No valid sources were selected.")
        else:
            print("No valid sources selected. Exiting.")
        return

    log(f"Start | query={args.query!r}, items={args.items}, outdir={outdir}, threads={args.threads}, sources={srcs}")
    assets = gather_assets(srcs, args.query, args.items, keys)

    if not assets:
        log("No assets found. Try a broader query or enable more sources.")
        if GUI_AVAILABLE and args.gui:
            messagebox.showinfo("No Results", "No assets found. Please try a different query.")
        else:
            print("No assets found.")
        return

    if args.gui:
        # We came from SettingsGUI, now show PreviewGUI in a new window.
        preview_root = tk.Toplevel()
        app = PreviewGUI(preview_root, assets, outdir, args.threads)
        preview_root.mainloop()
    else:
        # Headless: download all
        results = download_assets(outdir, assets, threads=args.threads)
        manifest = {"generated_at": time.time(), "results": results}
        write_manifest(outdir, manifest)
        okc = sum(1 for r in results if r.get("ok"))
        log(f"Finished headless downloads: {okc}/{len(results)} ok")
        print(f"Done. Downloaded {okc}/{len(results)} assets to: {outdir}")

def parse_args():
    p = argparse.ArgumentParser(
        prog="prf_media_downloader",
        description="PRF bulk downloader for royalty-free images/videos (GUI & CLI)."
    )
    p.add_argument("-q", "--query", default="nature", help="Search query/keyword")
    p.add_argument("-n", "--items", type=int, default=DEFAULT_ITEMS, help="Items per selected source (default: 10)")
    p.add_argument("-o", "--outdir", default=DEFAULT_OUT, help=f"Output folder (default: {DEFAULT_OUT})")
    p.add_argument("-t", "--threads", type=int, default=DEFAULT_THREADS, help=f"Download threads (default: {DEFAULT_THREADS})")
    p.add_argument("-s", "--sources", default=",".join(ALL_SOURCES),
                   help=f"Comma list from: {', '.join(ALL_SOURCES)}")
    p.add_argument("--gui", action="store_true", help="Launch GUI preview/selection")
    p.add_argument("--no-scrape", action="store_true", help="Disable scraping sources (Coverr, Mixkit, Videvo)")
    p.add_argument("--unsplash-key", help="Unsplash API key (overrides env)")
    p.add_argument("--pexels-key", help="Pexels API key (overrides env)")
    p.add_argument("--pixabay-key", help="Pixabay API key (overrides env)")
    return p.parse_args()

def main():
    args = parse_args()

    if args.gui:
        if not GUI_AVAILABLE:
            log("GUI not available in this environment. Use CLI mode.")
            print("GUI not available. Try CLI without --gui.")
            sys.exit(1)
        if not PIL_AVAILABLE:
            log("Pillow not installed; cannot show previews. Re-run installer.")
            print("Pillow not installed; cannot show previews. Re-run installer.")
            sys.exit(1)
        
        root = tk.Tk()
        app = SettingsGUI(root, args)
        root.mainloop()
    else:
        run_app_logic(args)


if __name__ == "__main__":
    # Graceful Ctrl+C
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    main()
