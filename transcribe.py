#!/usr/bin/env python3
"""Batch transcribe video files with AssemblyAI and generate HTML analysis reports with Claude.

Usage:
    python transcribe.py <folder>                # process all videos in folder
    python transcribe.py <folder> --out <dir>    # custom output location
    python transcribe.py <folder> --force        # reprocess even if report exists
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import PART_1_PROMPT, PART_2_PROMPT_TEMPLATE

CLAUDE_MODEL = "claude-sonnet-4-6"
SUPPORTED_EXTS = {".mp4", ".m4a", ".mp3", ".wav", ".mov", ".mkv", ".webm"}

AAI_BASE = "https://api.assemblyai.com"
AAI_SPEECH_MODELS = ["universal-3-pro", "universal-2"]
UPLOAD_CHUNK = 5 * 1024 * 1024  # 5 MiB


def fmt_ts(ms) -> str:
    if ms is None:
        return "00:00:00"
    total_seconds = int(ms) // 1000
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _aai_upload(file_path: Path, api_key: str) -> str:
    """Stream-upload a local file to AssemblyAI. Returns the temporary upload URL."""
    def _chunks(path: Path):
        with open(path, "rb") as f:
            while True:
                data = f.read(UPLOAD_CHUNK)
                if not data:
                    break
                yield data

    headers = {"authorization": api_key}
    resp = requests.post(f"{AAI_BASE}/v2/upload", headers=headers, data=_chunks(file_path))
    resp.raise_for_status()
    return resp.json()["upload_url"]


def transcribe(video_path: Path, api_key: str) -> dict:
    """Transcribe with speaker labels via AssemblyAI REST API."""
    headers = {"authorization": api_key}

    print("    uploading...", flush=True)
    audio_url = _aai_upload(video_path, api_key)

    print("    requesting transcription...", flush=True)
    create_resp = requests.post(
        f"{AAI_BASE}/v2/transcript",
        headers=headers,
        json={
            "audio_url": audio_url,
            "speech_models": AAI_SPEECH_MODELS,
            "speaker_labels": True,
        },
    )
    create_resp.raise_for_status()
    transcript_id = create_resp.json()["id"]

    poll_url = f"{AAI_BASE}/v2/transcript/{transcript_id}"
    print("    polling", end="", flush=True)
    while True:
        result = requests.get(poll_url, headers=headers).json()
        status = result.get("status")
        if status == "completed":
            print(" done.", flush=True)
            break
        if status == "error":
            print(flush=True)
            raise RuntimeError(f"AssemblyAI transcription error: {result.get('error')}")
        print(".", end="", flush=True)
        time.sleep(5)

    utterances = []
    lines = []
    for utt in (result.get("utterances") or []):
        utterances.append({
            "speaker": utt.get("speaker"),
            "start_ms": utt.get("start"),
            "end_ms": utt.get("end"),
            "text": utt.get("text"),
        })
        lines.append(f"[{fmt_ts(utt.get('start'))}] Speaker {utt.get('speaker')}: {utt.get('text')}")

    if not lines and result.get("text"):
        lines.append(result["text"])

    # API returns audio_duration in seconds
    duration_seconds = result.get("audio_duration")

    return {
        "id": transcript_id,
        "duration_seconds": duration_seconds,
        "text": result.get("text"),
        "utterances": utterances,
        "formatted": "\n".join(lines),
    }


def call_claude(client: Anthropic, transcript_text: str, instruction: str, max_tokens: int) -> str:
    """Single Claude call (streaming). Transcript is sent as a cached content block."""
    chunks: list[str] = []
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"<transcript>\n{transcript_text}\n</transcript>",
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": instruction},
            ],
        }],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)
    return "".join(chunks)


def strip_html_fence(s: str) -> str:
    """Strip ```html ... ``` fences if Claude included them despite instructions."""
    s = s.strip()
    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1 :]
        if s.endswith("```"):
            s = s[: s.rfind("```")]
    return s.strip()


def process_video(video_path: Path, out_dir: Path, anthropic_client: Anthropic, aai_key: str, force: bool) -> None:
    name = video_path.stem
    target = out_dir / name
    target.mkdir(parents=True, exist_ok=True)

    transcript_file = target / "transcript.json"
    context_file = target / "session_context.txt"
    report_file = target / "report.html"

    if report_file.exists() and not force:
        print(f"  Skipping (report exists): {report_file.name}")
        return

    # 1. Transcribe (cached)
    if transcript_file.exists() and not force:
        print("  Using cached transcript")
        data = json.loads(transcript_file.read_text(encoding="utf-8"))
    else:
        t0 = time.time()
        print("  Transcribing with AssemblyAI (this can take several minutes for long videos)...")
        data = transcribe(video_path, aai_key)
        transcript_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        dur = data.get("duration_seconds")
        dur_str = f"{dur//60}m{dur%60}s" if dur else "unknown duration"
        print(f"  Transcribed ({dur_str}, {len(data['utterances'])} utterances) in {time.time()-t0:.0f}s")

    transcript_text = data["formatted"]

    # 2. Session Context (cached)
    if context_file.exists() and not force:
        print("  Using cached session context")
        session_context = context_file.read_text(encoding="utf-8")
    else:
        t0 = time.time()
        print("  Generating Session Context with Claude...")
        session_context = call_claude(anthropic_client, transcript_text, PART_1_PROMPT, max_tokens=4000)
        context_file.write_text(session_context, encoding="utf-8")
        print(f"  Session Context done in {time.time()-t0:.0f}s")

    # 3. HTML report
    t0 = time.time()
    print("  Generating HTML report with Claude...")
    part2 = PART_2_PROMPT_TEMPLATE.replace("[session context input]", session_context)
    html = call_claude(anthropic_client, transcript_text, part2, max_tokens=32000)
    html = strip_html_fence(html)
    report_file.write_text(html, encoding="utf-8")
    print(f"  Report done in {time.time()-t0:.0f}s -> {report_file}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch transcribe videos and generate HTML analysis reports.")
    parser.add_argument("folder", type=Path, help="Folder containing video files")
    parser.add_argument("--out", type=Path, default=None, help="Output folder (default: <folder>/reports)")
    parser.add_argument("--force", action="store_true", help="Reprocess even if cached output exists")
    args = parser.parse_args()

    load_dotenv()
    aai_key = os.environ.get("ASSEMBLYAI_API_KEY", "").strip()
    ant_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not aai_key or aai_key.startswith("PASTE_") or not ant_key or ant_key.startswith("PASTE_"):
        print("ERROR: set ASSEMBLYAI_API_KEY and ANTHROPIC_API_KEY in .env", file=sys.stderr)
        return 1
    anthropic_client = Anthropic(api_key=ant_key)

    folder = args.folder.resolve()
    if not folder.is_dir():
        print(f"ERROR: {folder} is not a directory", file=sys.stderr)
        return 1

    out_dir = (args.out or (folder / "reports")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS)
    if not videos:
        print(f"No videos found in {folder} (looking for: {sorted(SUPPORTED_EXTS)})")
        return 0

    print(f"Found {len(videos)} video(s). Output -> {out_dir}\n")
    failures = 0
    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video.name}")
        try:
            process_video(video, out_dir, anthropic_client, aai_key, force=args.force)
        except Exception as e:
            failures += 1
            print(f"  FAILED: {e}", file=sys.stderr)
        print()

    print(f"Done. {len(videos) - failures} succeeded, {failures} failed.")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
