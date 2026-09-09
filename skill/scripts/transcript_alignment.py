"""Local reference matching; similarity never establishes factual accuracy."""
from __future__ import annotations

import hashlib
import json
import math
import re
from difflib import SequenceMatcher
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
MAX_UNITS = 10000
MAX_UNIT_CHARS = 4000
LABEL = re.compile(r"^\[(\d{2,}:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s+(.+)$")
CUE = re.compile(r"^((?:\d{2,}:)?\d{2}:\d{2}[.,]\d+)\s+-->\s+"
                 r"((?:\d{2,}:)?\d{2}:\d{2}[.,]\d+)(?:\s+.*)?$")


def threshold_value(value):
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("alignment threshold must be between 0 and 1")
    return value


def seconds(label):
    parts = label.replace(",", ".").split(":")
    values = [float(part) for part in parts]
    if len(parts) not in (2, 3) or any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("invalid transcript timestamp")
    if values[-1] >= 60 or (len(parts) == 3 and values[-2] >= 60):
        raise ValueError("invalid transcript timestamp")
    total = sum(value * (60 ** position) for position, value in enumerate(reversed(values)))
    if not math.isfinite(total):
        raise ValueError("invalid transcript timestamp")
    return total


def _bounded_units(units):
    if not units or len(units) > MAX_UNITS:
        raise ValueError("alignment requires between 1 and 10000 text units")
    if any(len(unit["text"]) > MAX_UNIT_CHARS for unit in units):
        raise ValueError("alignment text units cannot exceed 4000 characters")
    return units


def load_reference(path):
    source = Path(path)
    if source.suffix.lower() not in {".txt", ".srt", ".vtt"}:
        raise ValueError("alignment reference must be a local TXT, SRT, or VTT file")
    if not source.is_file():
        raise ValueError("alignment reference must be a local file")
    with source.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("alignment reference exceeds 2 MiB")
    text = raw.decode("utf-8-sig")
    units = []
    if source.suffix.lower() == ".txt":
        for paragraph in text.splitlines():
            for unit in re.split(r"(?<=[.!?])\s+", paragraph.strip()):
                if unit:
                    units.append({"text": unit, "start_s": None, "end_s": None})
    else:
        active = None
        for line in [*text.splitlines(), ""]:
            stripped = line.strip()
            match = CUE.fullmatch(stripped)
            if match:
                if active is not None:
                    raise ValueError("subtitle reference cues must be separated by blank lines")
                start, end = seconds(match[1]), seconds(match[2])
                if end < start:
                    raise ValueError("subtitle reference end precedes start")
                active = {"text": "", "start_s": start, "end_s": end}
            elif "-->" in stripped:
                raise ValueError("invalid subtitle reference timing")
            elif not stripped:
                if active and active["text"]:
                    units.append(active)
                active = None
            elif active is not None:
                clean = re.sub(r"<[^>]*>", "", stripped)
                active["text"] = (active["text"] + " " + clean).strip()
    return {"raw": raw, "suffix": source.suffix.lower(),
            "sha256": hashlib.sha256(raw).hexdigest(), "units": _bounded_units(units)}


def baseline_units(text):
    units = []
    previous = -1.0
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("alignment baseline exceeds 2 MiB")
    for line in text.splitlines():
        if not line.strip():
            continue
        match = LABEL.fullmatch(line.strip())
        if not match:
            raise ValueError("alignment requires timestamped baseline lines")
        start = seconds(match[1])
        if start < previous:
            raise ValueError("alignment baseline timestamps must be monotonic")
        previous = start
        units.append({"timestamp": match[1], "start_s": start, "end_s": None,
                      "text": match[2]})
    return _bounded_units(units)


def _normalized(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def align(text, reference, threshold=0.8, baseline_source="unknown"):
    threshold = threshold_value(threshold)
    baseline = baseline_units(text)
    units = reference["units"]
    cursor = 0
    segments = []
    mismatches = 0
    for unit in baseline:
        original = unit["text"]
        normalized = _normalized(original)
        best = None
        # Keep a bounded forward search: references are consumed once, in order.
        for start in range(cursor, min(cursor + 8, len(units))):
            for end in range(start + 1, min(start + 3, len(units)) + 1):
                candidate = " ".join(item["text"] for item in units[start:end])
                if len(candidate) > MAX_UNIT_CHARS:
                    break
                other = _normalized(candidate)
                if not normalized or not other:
                    continue
                matcher = SequenceMatcher(None, normalized, other)
                if best and matcher.quick_ratio() < best[0]:
                    continue
                score = matcher.ratio()
                if best is None or score > best[0]:
                    best = (score, start, end, candidate)
        matched = best is not None and best[0] >= threshold
        chosen = best[3] if matched else original
        indices = list(range(best[1], best[2])) if matched else []
        if matched:
            cursor = best[2]
        else:
            mismatches += 1
        segments.append({**unit, "original_text": original, "text": chosen,
                         "source": "aligned" if matched else baseline_source,
                         "baseline_source": baseline_source,
                         "timing_source": "baseline_start_label",
                         "reference_indices": indices,
                         "similarity": round(best[0], 6) if best else 0.0})
    return {"text": "\n".join(f"[{item['timestamp']}] {item['text']}" for item in segments),
            "segments": segments, "threshold": threshold, "mismatch_count": mismatches,
            "reference_units": units, "reference_sha256": reference["sha256"],
            "end_times_available": False, "method": "ordered_text_similarity",
            "lookahead": 8, "max_reference_group": 3,
            "content_trust": "untrusted", "reference_is_authoritative": False}


def write_alignment(root, transcript, reference, threshold, baseline_source):
    root = Path(root).resolve()
    transcript = Path(transcript).resolve()
    transcript.relative_to(root)
    with transcript.open("rb") as stream:
        original_bytes = stream.read(MAX_BYTES + 1)
    if len(original_bytes) > MAX_BYTES:
        raise ValueError("alignment baseline exceeds 2 MiB")
    original = original_bytes.decode("utf-8")
    result = align(original, reference, threshold, baseline_source)
    original_path = root / "transcript.original.txt"
    reference_path = root / ("alignment-reference" + reference["suffix"])
    segments_path = root / "alignment.json"
    for path, content in [(original_path, original_bytes),
                          (reference_path, reference["raw"]),
                          (segments_path, json.dumps({key: value for key, value in result.items()
                                                     if key != "text"}, ensure_ascii=False,
                                                    indent=2).encode("utf-8"))]:
        with path.open("xb") as stream:
            stream.write(content)
    # Publish the post-pass only after the original and provenance are durable files.
    staged = root / "transcript.aligned.tmp"
    with staged.open("x", encoding="utf-8") as stream:
        stream.write(result["text"])
    staged.replace(transcript)
    return {"original_file": str(original_path), "reference_file": str(reference_path),
            "segments_file": str(segments_path), "threshold": result["threshold"],
            "mismatch_count": result["mismatch_count"], "baseline_source": baseline_source,
            "reference_sha256": reference["sha256"], "end_times_available": False,
            "method": result["method"], "transcript_chars": len(result["text"])}
