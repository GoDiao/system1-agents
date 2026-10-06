"""Render a multi-snake recording to MP4/PNG at its real recorded speed."""

import argparse
import hashlib
import json
import shutil
import subprocess
from collections import deque
from pathlib import Path

from .multi_ui import compose_multi
from .replay import TerminalRaster, ffmpeg_mp4_cmd


def load_multi(path):
    metadata, frames, summary = None, [], None
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if event["type"] == "metadata":
            metadata = event
        elif event["type"] == "frame":
            frames.append(event)
        elif event["type"] == "end":
            summary = event["summary"]
    if metadata is None or not frames:
        raise ValueError("Recording must contain metadata and frames")
    return metadata, frames, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--output", type=Path, required=True, help=".mp4 or .png")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--cols", type=int, default=4)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new filename")

    metadata, frames, summary = load_multi(args.recording)
    seeds = sorted({f["seed"] for f in frames})
    times = [f["at"] for f in frames]
    start, end = max(times[0], args.start), min(max(times[0], args.start) + args.seconds, times[-1])

    state = {}
    recent = deque()
    cursor = 0

    def advance(t):
        nonlocal cursor
        while cursor < len(frames) and frames[cursor]["at"] <= t:
            f = frames[cursor]
            state[f["seed"]] = f
            recent.append(f)
            cursor += 1
        while recent and recent[0]["at"] < t - 2.0:
            recent.popleft()

    def stats_at(t):
        alive = sum(1 for s in seeds if state.get(s, {}).get("game", {}).get("alive", True))
        dps = len([f for f in recent if f["at"] > t - 1.0]) if recent else 0
        ms = [f["decision"].get("inference_ms", 0) for f in recent if f.get("decision")]
        return {
            "alive": alive,
            "dps": dps,
            "mean_ms": sum(ms) / len(ms) if ms else 0,
            "score": sum(s["game"]["score"] for s in state.values()),
            "clock": f"{int(t) // 60:02d}:{int(t) % 60:02d}",
        }

    advance(start)
    canvas = compose_multi([state[s] for s in seeds if s in state], stats_at(start), args.cols)
    raster = TerminalRaster(canvas.width, canvas.height, width=1920, height=1080)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix == ".png":
        raster.render(canvas).save(args.output)
        print(args.output)
        return 0
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.error("MP4 export needs ffmpeg")
    count = max(1, int((end - start) * args.fps))
    process = subprocess.Popen(ffmpeg_mp4_cmd(ffmpeg, args.output, args.fps), stdin=subprocess.PIPE)
    try:
        for index in range(count):
            t = start + index / args.fps
            advance(t)
            pixels = raster.render(
                compose_multi([state[s] for s in seeds if s in state], stats_at(t), args.cols)
            ).tobytes()
            process.stdin.write(pixels)
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("ffmpeg did not complete the MP4")
    except BaseException:
        process.kill()
        process.wait()
        raise
    sidecar = {
        "source_recording": args.recording.name,
        "source_sha256": hashlib.sha256(args.recording.read_bytes()).hexdigest(),
        "model": metadata["model"],
        "playback_speed": 1,
        "video_fps": args.fps,
        "video_frames": count,
        "session_summary": summary,
    }
    args.output.with_suffix(".json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(json.dumps({"video": str(args.output), "seconds": count / args.fps}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
