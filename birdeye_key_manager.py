#!/usr/bin/env python3
"""Birdeye API key manager and rotator.

Tätä skriptiä voi käyttää uusien Birdeye API -avaimien tallentamiseen ja
vuorotteluun. Avaimet säilytetään repossa polussa `configs/birdeye_keys.json`
(formaatti: {"keys": ["..."]}). Lisäksi viimeksi käytetty avain pidetään
käyttäjäkohtaisessa tilatiedostossa `~/.cache/matkatiimi_birdeye_state.json`.

Käyttöesimerkkejä:
    python3 birdeye_key_manager.py            # tulostaa seuraavan avaimen
    python3 birdeye_key_manager.py --list     # listaa tallennetut avaimet
    python3 birdeye_key_manager.py --add KEY  # lisää uuden avaimen
    python3 birdeye_key_manager.py --generate # generoi placeholder-avaimen

Jos avaimia ei ole, skripti yrittää käyttää ympäristömuuttujaa
`BIRDEYE_API_KEY`. Muussa tapauksessa käyttäjää pyydetään syöttämään avain.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path
from typing import List, Tuple

CONFIG_PATH = Path(__file__).resolve().parent / "configs" / "birdeye_keys.json"
STATE_PATH = Path.home() / ".cache" / "matkatiimi_birdeye_state.json"


def _ensure_cache_dir() -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass


def _load_keys() -> List[str]:
    keys: List[str] = []
    env_keys = os.getenv("BIRDEYE_API_KEYS")
    if env_keys:
        keys = [k.strip() for k in env_keys.split(",") if k.strip()]
        if keys:
            return keys

    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                keys = [k for k in data.get("keys", []) if isinstance(k, str)]
            elif isinstance(data, list):
                keys = [k for k in data if isinstance(k, str)]
        except json.JSONDecodeError:
            pass
        if keys:
            return keys

    # fallback to config.yaml via simple parse (lazy import to avoid dependency)
    yaml_path = Path(__file__).resolve().parent / "config.yaml"
    if yaml_path.exists():
        try:
            import yaml  # type: ignore

            cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            birdeye_cfg = (
                (cfg.get("io") or {}).get("birdeye")
                if isinstance(cfg.get("io"), dict)
                else None
            )
            if isinstance(birdeye_cfg, dict):
                key = birdeye_cfg.get("api_key")
                if isinstance(key, str) and key and "your" not in key.lower():
                    return [key]
        except Exception:
            pass

    env_single = os.getenv("BIRDEYE_API_KEY")
    if env_single:
        return [env_single]
    return []


def _save_keys(keys: List[str]) -> None:
    data = {"keys": keys, "count": len(keys)}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_state() -> Tuple[int, int]:
    _ensure_cache_dir()
    if not STATE_PATH.exists():
        return 0, 0
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        idx = int(state.get("index", 0))
        rev = int(state.get("revision", 0))
        return idx, rev
    except Exception:
        return 0, 0


def _store_state(index: int, revision: int) -> None:
    _ensure_cache_dir()
    STATE_PATH.write_text(json.dumps({"index": index, "revision": revision}), encoding="utf-8")


def _next_key(keys: List[str]) -> str:
    if not keys:
        raise RuntimeError("Birdeye-avaimia ei ole tallennettu. Lisää avain --add lipulla.")
    index, revision = _load_state()
    index = (index + 1) % len(keys)
    _store_state(index, revision)
    return keys[index]


def _current_key(keys: List[str]) -> str:
    if not keys:
        raise RuntimeError("Birdeye-avaimia ei ole tallennettu. Lisää avain --add lipulla.")
    index, _ = _load_state()
    index = min(index, len(keys) - 1)
    return keys[index]


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Birdeye API key manager")
    parser.add_argument("--list", action="store_true", help="Listaa tallennetut avaimet")
    parser.add_argument("--current", action="store_true", help="Näytä nykyinen avain")
    parser.add_argument("--next", action="store_true", help="Palauta seuraava avain (oletus)")
    parser.add_argument("--add", metavar="KEY", help="Lisää uusi avain")
    parser.add_argument("--remove", metavar="KEY", help="Poista avain")
    parser.add_argument("--generate", action="store_true", help="Luo satunnainen 32-merkkinen placeholder-avain")
    parser.add_argument("--quiet", action="store_true", help="Tulosta vain avain ilman lisätekstiä")
    args = parser.parse_args(argv or sys.argv[1:])

    keys = _load_keys()

    if args.add:
        key = args.add.strip()
        if len(key) < 8:
            print("⚠️ Avain on liian lyhyt", file=sys.stderr)
            return 1
        if key not in keys:
            keys.append(key)
            _save_keys(keys)
        if not args.quiet:
            print(f"✅ Avain lisätty (nyt {len(keys)} kpl)")
        if not args.list and not args.current and not args.next:
            return 0

    if args.remove:
        key = args.remove.strip()
        if key in keys:
            keys.remove(key)
            _save_keys(keys)
            if not args.quiet:
                print(f"🗑️ Avain poistettu. Jäljellä {len(keys)} kpl")
        else:
            print("⚠️ Avain ei löydy listalta", file=sys.stderr)
            return 1
        if not args.list and not args.current and not args.next:
            return 0

    if args.generate:
        placeholder = secrets.token_hex(16)
        if placeholder not in keys:
            keys.append(placeholder)
            _save_keys(keys)
        if not args.quiet:
            print("🔧 Luotiin uusi placeholder-avain (muista korvata oikealla avaimella)")
        if not args.current and not args.next and not args.list:
            print(placeholder)
            return 0

    if not keys:
        # Interaktiivinen lisäys
        if sys.stdin.isatty():
            try:
                key = input("Syötä Birdeye API key: ").strip()
            except EOFError:
                key = ""
            if key:
                keys.append(key)
                _save_keys(keys)
            else:
                print("❌ Avain puuttuu", file=sys.stderr)
                return 1
        else:
            print("❌ Birdeye-avaimia ei ole eikä interaktiivinen syöttö ole mahdollinen", file=sys.stderr)
            return 1

    if args.list:
        for idx, key in enumerate(keys, start=1):
            print(f"{idx}. {key}")
        return 0

    if args.current:
        key = _current_key(keys)
        if args.quiet:
            print(key)
        else:
            print(f"🔑 Nykyinen Birdeye-avain: {key}")
        return 0

    # default => next
    key = _next_key(keys)
    if args.quiet:
        print(key)
    else:
        print(f"🔄 Seuraava Birdeye-avain: {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
