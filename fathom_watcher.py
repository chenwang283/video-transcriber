#!/usr/bin/env python3
"""Poll Fathom API for new meeting transcripts and generate Markdown analysis reports with Claude.

Usage:
    python fathom_watcher.py                   # watch for new meetings, output -> ./reports/
    python fathom_watcher.py --out <dir>       # custom output directory
    python fathom_watcher.py --interval <sec>  # poll interval in seconds (default: 60)
    python fathom_watcher.py --force           # reprocess already-processed meetings
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from anthropic import Anthropic
from dotenv import load_dotenv

from prompts import PART_1_PROMPT, PART_2_PROMPT_TEMPLATE

CLAUDE_MODEL = "claude-sonnet-4-6"
FATHOM_API_BASE = "https://api.fathom.ai"
STATE_FILENAME = "processed_meetings.json"


def fmt_ts(seconds) -> str:
    if seconds is None:
        return "00:00:00"
    total_seconds = int(float(seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def fetch_meetings(api_key: str) -> list[dict]:
    """Fetch all meetings with transcripts from the Fathom REST API."""
    resp = requests.get(
        f"{FATHOM_API_BASE}/external/v1/meetings",
        headers={"X-Api-Key": api_key},
        params={"include_transcript": "true"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("meetings", data.get("data", []))


def format_transcript(meeting: dict) -> str:
    """Convert a Fathom meeting's transcript to [HH:MM:SS] Speaker: text lines."""
    transcript = meeting.get("transcript") or []

    # Transcript may be a dict wrapping a list
    if isinstance(transcript, dict):
        transcript = transcript.get("utterances", transcript.get("segments", []))

    lines = []
    for utt in transcript:
        speaker = utt.get("speaker") or utt.get("speaker_name") or "Unknown"
        start = utt.get("start_time") or utt.get("start") or 0
        # Detect milliseconds (large values) vs seconds
        if isinstance(start, (int, float)) and start > 10000:
            start = start / 1000
        text = utt.get("text") or utt.get("content") or ""
        lines.append(f"[{fmt_ts(start)}] {speaker}: {text}")

    if not lines:
        # Fallback to plain text if the API returns no utterances
        raw = meeting.get("transcript_text") or meeting.get("text") or ""
        if raw:
            lines.append(raw)

    return "\n".join(lines)


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def load_state(state_file: Path) -> set:
    if state_file.exists():
        return set(json.loads(state_file.read_text(encoding="utf-8")))
    return set()


def save_state(state_file: Path, processed: set) -> None:
    state_file.write_text(json.dumps(sorted(processed), indent=2), encoding="utf-8")


def call_claude(client: Anthropic, transcript_text: str, instruction: str, max_tokens: int) -> str:
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


def strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1:]
        if s.endswith("```"):
            s = s[:s.rfind("```")]
    return s.strip()


def run_analysis(transcript_text: str, target: Path, client: Anthropic, force: bool) -> None:
    context_file = target / "session_context.txt"
    report_file = target / "report.md"

    if report_file.exists() and not force:
        print("  Skipping (report already exists)")
        return

    if context_file.exists() and not force:
        print("  Using cached session context")
        session_context = context_file.read_text(encoding="utf-8")
    else:
        t0 = time.time()
        print("  Generating session context with Claude...")
        session_context = call_claude(client, transcript_text, PART_1_PROMPT, max_tokens=4000)
        context_file.write_text(session_context, encoding="utf-8")
        print(f"  Session context done in {time.time()-t0:.0f}s")

    t0 = time.time()
    print("  Generating report with Claude...")
    part2 = PART_2_PROMPT_TEMPLATE.replace("[session context input]", session_context)
    md = call_claude(client, transcript_text, part2, max_tokens=32000)
    report_file.write_text(strip_fence(md), encoding="utf-8")
    print(f"  Report done in {time.time()-t0:.0f}s -> {report_file}")


def process_meeting(meeting: dict, out_dir: Path, client: Anthropic, force: bool) -> None:
    title = meeting.get("title") or meeting.get("name") or "untitled"
    date_prefix = (meeting.get("created_at") or meeting.get("recorded_at") or "")[:10]
    folder_name = sanitize(f"{date_prefix}_{title}" if date_prefix else title)
    target = out_dir / folder_name
    target.mkdir(parents=True, exist_ok=True)

    transcript_text = format_transcript(meeting)
    if not transcript_text.strip():
        print("  Skipping: transcript is empty")
        return

    (target / "transcript.txt").write_text(transcript_text, encoding="utf-8")
    run_analysis(transcript_text, target, client, force)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch Fathom for new meetings and generate Markdown analysis reports.")
    parser.add_argument("--out", type=Path, default=None, help="Output folder (default: ./reports)")
    parser.add_argument("--interval", type=int, default=60, help="Poll interval in seconds (default: 60)")
    parser.add_argument("--force", action="store_true", help="Reprocess already-processed meetings")
    args = parser.parse_args()

    load_dotenv()
    fathom_key = os.environ.get("FATHOM_API_KEY", "").strip()
    ant_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not fathom_key or not ant_key:
        print("ERROR: set FATHOM_API_KEY and ANTHROPIC_API_KEY in .env", file=sys.stderr)
        return 1

    client = Anthropic(api_key=ant_key)
    out_dir = (args.out or Path("reports")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    state_file = out_dir / STATE_FILENAME

    print(f"Output -> {out_dir}")
    print(f"Poll interval: {args.interval}s\n")

    processed = load_state(state_file)

    # First run: mark all existing meetings as seen so they are not reprocessed
    if not processed:
        print("First run — marking existing meetings as already processed...")
        try:
            meetings = fetch_meetings(fathom_key)
            for m in meetings:
                processed.add(str(m["id"]))
            save_state(state_file, processed)
            print(f"Marked {len(meetings)} existing meeting(s) as seen. Watching for new ones.\n")
        except Exception as e:
            print(f"ERROR on first run: {e}", file=sys.stderr)
            return 1

    print("Watching for new Fathom meetings... (Ctrl+C to stop)\n")
    try:
        while True:
            try:
                meetings = fetch_meetings(fathom_key)
                new = [m for m in meetings if str(m["id"]) not in processed]
                if new:
                    print(f"Found {len(new)} new meeting(s).")
                for meeting in new:
                    title = meeting.get("title") or meeting.get("name") or meeting["id"]
                    print(f"[new] {title}")
                    try:
                        process_meeting(meeting, out_dir, client, force=args.force)
                        processed.add(str(meeting["id"]))
                        save_state(state_file, processed)
                    except Exception as e:
                        print(f"  FAILED: {e}", file=sys.stderr)
                        # Not added to processed — will retry on next poll
            except requests.RequestException as e:
                print(f"Network error: {e}", file=sys.stderr)

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
