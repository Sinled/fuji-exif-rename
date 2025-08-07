#!/usr/bin/env python3
"""
xt5_exif_tool.py

Standalone EXIF dumper & renamer for Fujifilm X-T5 images.

When run with -v/--verbose, logs detailed EXIF & processing info only to xt5_exif_tool.log
and prints a one-line notice to stderr. Without -v, no logging is performed
and only filenames are printed to stdout.

Pass `--rename` to actually rename each file to its new name.
"""

import sys
import os
import subprocess
import json
import logging
import argparse
from typing import List, Optional, Any

LOG_FILE = "xt5_exif_tool.log"

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

def build_new_name(filepath: str, exif: dict) -> str:
    fname = os.path.basename(filepath)
    base, ext = os.path.splitext(fname)

    pic_mode = fetch(exif, "PictureMode", "")
    seq_val  = fetch(exif, "SequenceNumber", 0)
    drive    = fetch(exif, "DriveMode", "")
    film     = fetch(exif, "FilmMode", "")
    adv      = fetch(exif, "AdvancedFilter", "")
    sat      = fetch(exif, "Saturation", "")

    try:
        seq = int(seq_val)
    except Exception:
        seq = 0

    tags: List[str] = []

    # HDR
    if isinstance(pic_mode, str) and "HDR" in pic_mode:
        tags.append("[HDR]")
        logging.debug("Applied HDR tag")

    # DriveMode + SequenceNumber (EB for Single+Auto bracket)
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

    # FilmMode (capture name_clean for later)
    film_tag_name: Optional[str] = None
    if isinstance(film, str) and film.strip():
        if "(" in film and ")" in film:
            name = film.split("(", 1)[1].split(")", 1)[0].strip()
        else:
            name = film.strip()
        film_tag_name = name.replace(" ", "")
        tags.append(f"[{film_tag_name}]")
        logging.debug(f"Applied FilmMode tag: {film_tag_name}")

    # AdvancedFilter
    if isinstance(adv, str) and adv.strip():
        af = adv.replace(" ", "")
        tags.append(f"[{af}]")
        logging.debug(f"Applied AdvancedFilter tag: {af}")

    # Saturation (skip if film_tag_name present or exactly "0 (normal)")
    if film_tag_name is None and isinstance(sat, str):
        sc = sat.strip()
        if sc and sc.lower() != "0 (normal)":
            sat_tag = sc.replace(" ", "")
            tags.append(f"[{sat_tag}]")
            logging.debug(f"Applied Saturation tag: {sat_tag}")

    suffix = "_" + "".join(tags) if tags else ""
    return f"{base}{suffix}{ext}"

def main():
    parser = argparse.ArgumentParser(description="xt5_exif_tool")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="enable logging to file")
    parser.add_argument("--rename", action="store_true",
                        help="actually rename files")
    parser.add_argument("images", nargs="*", help="image files to process")
    args = parser.parse_args()

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

    for img in images:
        if not os.path.isfile(img):
            logging.warning(f"Not found: {img}")
            continue
        exif = get_exif_via_exiftool(img)
        dump_all_exif(img, exif)
        newname = build_new_name(img, exif)
        dirpath = os.path.dirname(img) or "."
        dest = os.path.join(dirpath, newname)

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
