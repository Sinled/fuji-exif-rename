#!/usr/bin/env python3
"""
xt5_exif_tool.py

EXIF dumper & renamer for Fujifilm X-T5.
- Supports default recipes in custom_recipes.json
- Supports extra recipes via --recipes-json (prepended to override defaults)
- When -v is set, logs to xt5_exif_tool.log; otherwise prints only new names.

Pass --rename to actually rename files.
"""

import sys
import os
import subprocess
import json
import logging
import argparse
from typing import List, Any, Optional, Dict

LOG_FILE = "xt5_exif_tool.log"
RECIPES_FILE = os.path.join(os.path.dirname(__file__), "custom_recipes.json")

def setup_logging(verbose: bool):
    logger = logging.getLogger()
    logger.handlers.clear()
    if not verbose:
        logging.disable(logging.CRITICAL)
        return
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(fh)

def get_exif_via_exiftool(filepath: str) -> dict:
    try:
        res = subprocess.run(
            ["exiftool", "-json", "-G", filepath],
            capture_output=True, text=True, check=True
        )
        data = json.loads(res.stdout)
        logging.debug(f"Loaded EXIF for {filepath}")
        return data[0] if data else {}
    except FileNotFoundError:
        logging.error("exiftool not found. Install it first.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"exiftool error on {filepath}: {e}")
        return {}

def dump_all_exif(filepath: str, exif: dict) -> None:
    fname = os.path.basename(filepath)
    formatted = json.dumps(exif, indent=2, ensure_ascii=False)
    logging.info(f"--- Formatted EXIF for {fname} ---\n{formatted}")
    for tag, val in sorted(exif.items()):
        logging.debug(f"{tag}: {val}")

def fetch(exif: dict, tag_name: str, default: Optional[Any] = None) -> Any:
    for key, val in exif.items():
        if val is None:
            continue
        if key == tag_name or key.endswith(f":{tag_name}"):
            return val
    return default

def parse_recipes_json(s: Optional[str]) -> List[Dict[str, Any]]:
    if not s:
        return []
    try:
        data = json.loads(s)
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        logging.warning("recipes-json is not a list; ignoring.")
    except Exception as e:
        logging.warning(f"Failed to parse recipes-json: {e}")
    return []

def load_recipes(extra_json: Optional[str]) -> List[Dict[str, Any]]:
    # load defaults
    base: List[Dict[str, Any]] = []
    try:
        if os.path.isfile(RECIPES_FILE):
            with open(RECIPES_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    base = [r for r in loaded if isinstance(r, dict)]
                logging.debug(f"Loaded {len(base)} default recipes from {RECIPES_FILE}")
        else:
            logging.debug(f"No default recipes file at {RECIPES_FILE}")
    except Exception as e:
        logging.warning(f"Could not load default recipes: {e}")

    # load extras (prepend)
    extras = parse_recipes_json(extra_json)
    logging.debug(f"Loaded {len(extras)} extra recipes from CLI/env")

    merged = extras + base
    logging.info(f"Total recipes (extras+defaults): {len(merged)}")
    return merged

def match_recipe(exif: dict, recipes: List[Dict[str, Any]]) -> Optional[str]:
    """
    Return the first recipe name whose settings all match the EXIF.
    Logs each tag comparison: expected vs actual.
    """
    for rec in recipes:
        name = rec.get("name")
        settings = rec.get("settings", {})
        if not isinstance(settings, dict):
            continue
        all_match = True
        for tag, expected in settings.items():
            actual = fetch(exif, tag)
            logging.debug(f"Recipe '{name}' check: {tag}: expected '{expected}', got '{actual}'")
            if actual != expected:
                all_match = False
                break
        if all_match:
            logging.info(f"Matched recipe '{name}'")
            return name
    return None

def build_new_name(filepath: str, exif: dict, recipes: List[Dict[str, Any]]) -> str:
    fname = os.path.basename(filepath)
    base, ext = os.path.splitext(fname)

    # Try to match recipe first
    recipe_name = match_recipe(exif, recipes)

    tags: List[str] = []
    film_or_recipe_name: Optional[str] = None

    # 1) HDR
    pic_mode = fetch(exif, "PictureMode", "")
    if isinstance(pic_mode, str) and "HDR" in pic_mode:
        tags.append("[HDR]")
        logging.debug("Applied HDR tag")

    # 2) SequenceNumber + DriveMode
    seq_val = fetch(exif, "SequenceNumber", 0)
    drive   = fetch(exif, "DriveMode", "")
    try:
        seq = int(seq_val)
    except Exception:
        seq = 0

    seq_tag: Optional[str] = None
    if seq > 0 and isinstance(drive, str):
        if "Continuous Low" in drive:
            seq_tag = f"CL{seq:02d}"
        elif "Continuous High" in drive:
            seq_tag = f"CH{seq:02d}"
        elif "Single" in drive:
            exp = fetch(exif, "ExposureMode", "")
            if isinstance(exp, str) and "Auto bracket" in exp:
                seq_tag = f"EB{seq:02d}"
    if seq_tag:
        tags.append(f"[{seq_tag}]")
        logging.debug(f"Applied DriveMode tag: {seq_tag}")
    elif seq > 0:
        tags.append(f"[{seq:02d}]")
        logging.debug(f"Applied raw SequenceNumber tag: {seq:02d}")

    # 3) Film/Recipe tag
    if recipe_name:
        film_or_recipe_name = recipe_name.replace(" ", "")
        tags.append(f"[{film_or_recipe_name}]")
        logging.debug(f"Applied Recipe tag: {recipe_name}")
    else:
        film = fetch(exif, "FilmMode", "")
        if isinstance(film, str) and film.strip():
            if "(" in film and ")" in film:
                name = film.split("(", 1)[1].split(")", 1)[0].strip()
            else:
                name = film.strip()
            film_or_recipe_name = name.replace(" ", "")
            tags.append(f"[{film_or_recipe_name}]")
            logging.debug(f"Applied FilmMode tag: {name}")

    # 4) AdvancedFilter
    adv = fetch(exif, "AdvancedFilter", "")
    if isinstance(adv, str) and adv.strip():
        adv_clean = adv.replace(" ", "")
        tags.append(f"[{adv_clean}]")
        logging.debug(f"Applied AdvancedFilter tag: {adv}")

    # 5) Saturation — ONLY if no film/recipe tag was added and not "0 (normal)"
    if film_or_recipe_name is None:
        sat = fetch(exif, "Saturation", "")
        if isinstance(sat, str):
            sc = sat.strip()
            if sc and sc.lower() != "0 (normal)":
                sat_tag = sc.replace(" ", "")
                tags.append(f"[{sat_tag}]")
                logging.debug(f"Applied Saturation tag: {sc}")
    else:
        logging.debug("Skipped Saturation tag because Film/Recipe tag is present")

    suffix = "_" + "".join(tags) if tags else ""
    return f"{base}{suffix}{ext}"

def main():
    parser = argparse.ArgumentParser(description="xt5_exif_tool")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="enable logging to file")
    parser.add_argument("--rename", action="store_true",
                        help="actually rename files")
    parser.add_argument("--recipes-json", type=str, default=None,
                        help="JSON array of custom recipes to prepend (overrides defaults if matched)")
    parser.add_argument("images", nargs="*", help="image files to process")
    args = parser.parse_args()

    # Support env var fallback if arg not provided
    extra_recipes_json = args.recipes_json or os.environ.get("user_custom_recipes")

    # Determine image list: args.images or stdin
    if args.images:
        images = args.images
    else:
        stdin = sys.stdin.read().strip()
        if stdin:
            images = stdin.splitlines()
        else:
            parser.error("No input files provided")

    setup_logging(args.verbose)
    if args.verbose:
        sys.stderr.write(f"Logging enabled: details written to {LOG_FILE}\n")

    recipes = load_recipes(extra_recipes_json)

    for img in images:
        if not os.path.isfile(img):
            logging.warning(f"Not found: {img}")
            continue
        exif = get_exif_via_exiftool(img)
        dump_all_exif(img, exif)
        newname = build_new_name(img, exif, recipes)
        dest = os.path.join(os.path.dirname(img) or ".", newname)

        if args.rename:
            try:
                os.rename(img, dest)
                logging.info(f"Renamed: {img} → {dest}")
            except Exception as e:
                logging.error(f"Failed to rename {img}: {e}")
                sys.stderr.write(f"Error: could not rename {img}\n")
                continue

        print(newname)

if __name__ == "__main__":
    main()
