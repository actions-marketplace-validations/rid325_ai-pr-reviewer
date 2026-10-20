#!/usr/bin/env python3
"""Build the README demo video and lightweight animated preview."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1920, 1080
FPS = 24
SCENE_SECONDS = 5
BG = "#07111f"
PANEL = "#0d1b2a"
PANEL_2 = "#11243a"
TEXT = "#f4f7fb"
MUTED = "#9db0c6"
BLUE = "#4ea1ff"
GREEN = "#42d392"
AMBER = "#ffbf69"
RED = "#ff6b7a"


def font(size: int, mono: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = "/System/Library/Fonts/SFNSMono.ttf" if mono else "/System/Library/Fonts/SFNS.ttf"
    return ImageFont.truetype(path, size)


F_TITLE = font(72, bold=True)
F_H2 = font(45, bold=True)
F_BODY = font(31)
F_SMALL = font(25)
F_MONO = font(27, mono=True)
F_MONO_SMALL = font(23, mono=True)


def rounded(draw: ImageDraw.ImageDraw, box, fill, radius=24, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def label(draw, xy, text, fill=BLUE):
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=F_SMALL)
    w = bbox[2] - bbox[0]
    rounded(draw, (x, y, x + w + 34, y + 48), fill, 20)
    draw.text((x + 17, y + 9), text, font=F_SMALL, fill="#05101d")


def check(draw, x, y, text, color=GREEN):
    draw.ellipse((x, y, x + 34, y + 34), fill=color)
    draw.line((x + 9, y + 18, x + 15, y + 25, x + 27, y + 10), fill="#06111e", width=5)
    draw.text((x + 52, y - 1), text, font=F_BODY, fill=TEXT)


def header(draw, step, title, subtitle):
    label(draw, (90, 64), step)
    draw.text((90, 135), title, font=F_TITLE, fill=TEXT)
    draw.text((94, 228), subtitle, font=F_BODY, fill=MUTED)


def footer(draw, scene_index, scene_count):
    draw.text((90, 1010), "github.com/rid325/ai-pr-reviewer", font=F_SMALL, fill=MUTED)
    x0, x1, y = 1190, 1830, 1026
    draw.rounded_rectangle((x0, y, x1, y + 8), radius=4, fill="#263a50")
    end = x0 + (x1 - x0) * (scene_index + 1) / scene_count
    draw.rounded_rectangle((x0, y, end, y + 8), radius=4, fill=BLUE)


def scene_intro(draw):
    draw.ellipse((1450, -180, 2100, 470), fill="#102f57")
    draw.ellipse((-250, 740, 380, 1370), fill="#123c36")
    label(draw, (90, 80), "REVIEWBOT v2")
    draw.text((90, 180), "AI review you can\ndefend in production.", font=F_TITLE, fill=TEXT, spacing=12)
    draw.text((95, 385), "Untrusted pull-request diffs become bounded, validated,\nactionable GitHub review comments.", font=F_BODY, fill=MUTED, spacing=10)
    stats = [("25", "files dogfooded"), ("1,581", "changed lines"), ("23", "tests passing")]
    for idx, (value, caption) in enumerate(stats):
        x = 95 + idx * 410
        rounded(draw, (x, 570, x + 360, 760), PANEL, 26, "#1f3d5a")
        draw.text((x + 30, 605), value, font=F_TITLE, fill=GREEN if idx == 2 else BLUE)
        draw.text((x + 34, 700), caption, font=F_SMALL, fill=MUTED)
    rounded(draw, (1370, 550, 1810, 820), PANEL_2, 32, BLUE)
    draw.text((1420, 605), "PR opened", font=F_H2, fill=TEXT)
    draw.line((1590, 680, 1590, 745), fill=BLUE, width=8)
    draw.polygon([(1568, 730), (1612, 730), (1590, 760)], fill=BLUE)
    draw.text((1420, 770), "Review posted", font=F_H2, fill=GREEN)


def scene_ingest(draw):
    header(draw, "01 / INGEST", "Read the whole pull request", "Pagination, filtering and explicit handling for missing patches")
    rounded(draw, (90, 330, 780, 900), PANEL, 28, "#213a54")
    draw.text((130, 370), "Changed files", font=F_H2, fill=TEXT)
    files = [
        ("reviewbot/core.py", "+204", GREEN),
        ("reviewbot/runner.py", "+134", GREEN),
        ("package-lock.json", "ignored", MUTED),
        ("assets/demo.gif", "no patch", AMBER),
    ]
    for i, (name, status, color) in enumerate(files):
        y = 455 + i * 92
        rounded(draw, (125, y, 742, y + 66), PANEL_2, 16)
        draw.text((150, y + 17), name, font=F_MONO_SMALL, fill=TEXT)
        draw.text((570, y + 17), status, font=F_MONO_SMALL, fill=color)
    rounded(draw, (860, 330, 1830, 900), PANEL, 28, "#213a54")
    draw.text((910, 370), "GitHub files API", font=F_H2, fill=TEXT)
    for i in range(3):
        x = 930 + i * 270
        color = BLUE if i < 2 else GREEN
        rounded(draw, (x, 510, x + 210, 650), PANEL_2, 22, color)
        draw.text((x + 60, 540), f"page {i + 1}", font=F_SMALL, fill=TEXT)
        draw.text((x + 75, 590), "100" if i < 2 else "25", font=F_H2, fill=color)
    check(draw, 930, 735, "No changed file silently disappears")


def scene_bound(draw):
    header(draw, "02 / BOUND", "Make large reviews predictable", "Line budgets and chunking keep cost, latency and quota under control")
    stages = [
        ("1,581 lines", "incoming diff", BLUE),
        ("filters", "generated files", AMBER),
        ("4 chunks", "≤ 500 lines each", GREEN),
    ]
    for i, (big, small, color) in enumerate(stages):
        x = 95 + i * 585
        rounded(draw, (x, 410, x + 480, 690), PANEL, 30, color)
        draw.text((x + 45, 470), big, font=F_H2, fill=color)
        draw.text((x + 45, 550), small, font=F_BODY, fill=MUTED)
        if i < 2:
            draw.line((x + 500, 550, x + 555, 550), fill=MUTED, width=7)
            draw.polygon([(x + 545, 532), (x + 580, 550), (x + 545, 568)], fill=MUTED)
    check(draw, 110, 790, "Hard total budget: 4 × max_diff_lines")
    check(draw, 780, 790, "Right-side line numbers preserved")


def scene_models(draw):
    header(draw, "03 / RESILIENCE", "Recover from model capacity failures", "Bounded timeouts, ordered fallback and request pacing")
    rows = [
        ("gemini-3.5-flash-lite", "primary", "success", GREEN),
        ("gemini-3.1-flash-lite", "fallback", "ready", BLUE),
    ]
    for i, (model, role, status, color) in enumerate(rows):
        y = 385 + i * 150
        rounded(draw, (100, y, 1190, y + 112), PANEL, 22, "#213a54")
        draw.text((145, y + 30), model, font=F_MONO, fill=TEXT)
        draw.text((710, y + 34), role, font=F_SMALL, fill=MUTED)
        label(draw, (960, y + 30), status.upper(), color)
    rounded(draw, (1280, 385, 1825, 685), PANEL_2, 28, BLUE)
    draw.text((1330, 430), "Predictable latency", font=F_H2, fill=TEXT)
    draw.text((1335, 520), "60 s", font=F_TITLE, fill=BLUE)
    draw.text((1555, 555), "request timeout", font=F_SMALL, fill=MUTED)
    draw.text((1335, 615), "30 s pacing between chunks", font=F_SMALL, fill=MUTED)
    check(draw, 110, 770, "SDK retry storm disabled")
    check(draw, 110, 835, "Errors fail the Action instead of reporting false success")


def scene_validate(draw):
    header(draw, "04 / VALIDATE", "Never post raw model output", "Every finding must map back to a reviewed file and a real added line")
    rounded(draw, (90, 330, 1040, 910), "#0b1624", 26, "#29435e")
    draw.text((135, 370), "reviewbot/sample.py", font=F_MONO, fill=MUTED)
    code = [
        ("41", "+", "def average(total, count):", GREEN),
        ("42", "+", "    return total / count", GREEN),
    ]
    for i, (line, mark, src, color) in enumerate(code):
        y = 470 + i * 70
        draw.text((140, y), line, font=F_MONO, fill=MUTED)
        draw.text((210, y), mark, font=F_MONO, fill=color)
        draw.text((260, y), src, font=F_MONO, fill=TEXT)
    rounded(draw, (140, 650, 970, 830), PANEL_2, 22, BLUE)
    draw.text((180, 685), "[HIGH] count can be zero, causing", font=F_BODY, fill=TEXT)
    draw.text((180, 733), "a ZeroDivisionError on line 42.", font=F_BODY, fill=TEXT)
    draw.text((180, 785), "Suggested change: guard count first", font=F_SMALL, fill=GREEN)
    checks = ["file was reviewed", "line 42 is added", "severity is valid", "size is bounded", "duplicate removed"]
    for i, text in enumerate(checks):
        check(draw, 1160, 400 + i * 95, text)
    label(draw, (1160, 825), "HALLUCINATIONS REJECTED", RED)


def scene_post(draw):
    header(draw, "05 / POST", "Turn findings into useful GitHub feedback", "Inline suggestions, safe fallback, one summary and reusable outputs")
    rounded(draw, (90, 340, 900, 885), "#f7f9fb", 28, BLUE)
    draw.text((135, 385), "github-actions  Bot", font=F_H2, fill="#17212b")
    draw.text((135, 465), "[HIGH] Guard count before division.", font=F_BODY, fill="#17212b")
    rounded(draw, (135, 545, 850, 725), "#e8edf2", 16)
    draw.rectangle((135, 600, 850, 665), fill="#d9f7e8")
    draw.text((170, 558), "Suggested change", font=F_SMALL, fill="#52616f")
    draw.text((175, 615), "+ if count == 0: return 0", font=F_MONO_SMALL, fill="#166534")
    draw.text((135, 790), "Mapped to an actual added line", font=F_SMALL, fill="#52616f")
    rounded(draw, (1010, 340, 1830, 885), PANEL, 28, "#213a54")
    draw.text((1060, 385), "Reliable delivery", font=F_H2, fill=TEXT)
    check(draw, 1060, 485, "Inline review")
    check(draw, 1060, 570, "422 → general-comment fallback")
    check(draw, 1060, 655, "Idempotent summary")
    check(draw, 1060, 740, "issues_found / files_reviewed")


def scene_finish(draw):
    header(draw, "06 / PROVE", "Dogfooded, tested and containerized", "The action reviewed its own production refactor before release")
    cards = [
        ("23 / 23", "unit tests", GREEN),
        ("PASS", "Docker build", GREEN),
        ("PASS", "live PR review", GREEN),
    ]
    for i, (big, small, color) in enumerate(cards):
        x = 100 + i * 590
        rounded(draw, (x, 390, x + 500, 670), PANEL, 30, color)
        draw.text((x + 45, 450), big, font=F_TITLE, fill=color)
        draw.text((x + 48, 570), small, font=F_BODY, fill=MUTED)
    draw.text((100, 785), "ReviewBot v2", font=F_TITLE, fill=TEXT)
    draw.text((690, 815), "validated • bounded • observable", font=F_H2, fill=BLUE)
    label(draw, (100, 900), "github.com/rid325/ai-pr-reviewer", GREEN)


SCENES = [scene_intro, scene_ingest, scene_bound, scene_models, scene_validate, scene_post, scene_finish]


def render(scene_index: int, local_t: float) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    SCENES[scene_index](draw)
    footer(draw, scene_index, len(SCENES))
    fade = min(1.0, local_t / 0.35, (SCENE_SECONDS - local_t) / 0.35)
    if fade < 1:
        overlay = Image.new("RGB", image.size, BG)
        image = Image.blend(overlay, image, max(0.0, fade))
    return image


def build(output_dir: Path, ffmpeg: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mp4 = output_dir / "reviewbot-demo.mp4"
    gif = output_dir / "reviewbot-demo.gif"
    total_frames = len(SCENES) * SCENE_SECONDS * FPS
    command = [
        ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    preview = []
    for frame_number in range(total_frames):
        seconds = frame_number / FPS
        scene_index = min(int(seconds // SCENE_SECONDS), len(SCENES) - 1)
        local_t = seconds - scene_index * SCENE_SECONDS
        frame = render(scene_index, local_t)
        assert process.stdin is not None
        process.stdin.write(frame.tobytes())
        if frame_number % 6 == 0:
            preview.append(frame.resize((960, 540), Image.Resampling.LANCZOS).quantize(colors=128))
    assert process.stdin is not None
    process.stdin.close()
    if process.wait() != 0:
        raise SystemExit("ffmpeg failed")
    preview[0].save(
        gif,
        save_all=True,
        append_images=preview[1:],
        duration=250,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"wrote {mp4} ({mp4.stat().st_size / 1_000_000:.1f} MB)")
    print(f"wrote {gif} ({gif.stat().st_size / 1_000_000:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("assets"))
    parser.add_argument("--ffmpeg", default=os.getenv("FFMPEG") or shutil.which("ffmpeg"))
    args = parser.parse_args()
    if not args.ffmpeg:
        raise SystemExit("ffmpeg was not found; pass --ffmpeg or set FFMPEG")
    build(args.output_dir, args.ffmpeg)


if __name__ == "__main__":
    main()
