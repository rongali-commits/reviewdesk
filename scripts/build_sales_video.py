from __future__ import annotations

# ruff: noqa: E402, I001

import asyncio
import subprocess
import sys
from pathlib import Path

SHARED_PYDEPS = Path(__file__).resolve().parents[3] / "tmp" / "upwork-video" / "pydeps"
sys.path.insert(0, str(SHARED_PYDEPS))

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
WORK = WORKSPACE / "tmp" / "reviewdesk-video"
FRAMES = WORK / "frames"
ASSETS = ROOT / "sales-assets"
OUTPUT = ASSETS / "ReviewDesk-Marketplace-Demo.mp4"
NARRATION = ASSETS / "ReviewDesk-Marketplace-Narration.mp3"
SUBTITLES = ASSETS / "ReviewDesk-Marketplace-Narration.srt"
FRAMES.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1280, 720
BG = "#0A100E"
PANEL = "#15201C"
CREAM = "#F8F3E8"
MUTED = "#A9B4AE"
GREEN = "#173F3A"
MINT = "#BEE7C3"
ORANGE = "#F2A65A"
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_SEMIBOLD = Path(r"C:\Windows\Fonts\seguisb.ttf")
VOICE = "en-US-EmmaMultilingualNeural"
NARRATION_TEXT = "\n\n".join(
    [
        "Turn completed jobs into honest feedback and credible customer proof with ReviewDesk.",
        "ReviewDesk gives local businesses a branded review request and testimonial workflow.",
        (
            "Each customer receives the same private feedback form, with a clear public review "
            "option available regardless of rating."
        ),
        "Scheduled reminders stop automatically after a response.",
        (
            "Business owners track requests, responses, average rating, and customer comments "
            "in one focused dashboard."
        ),
        (
            "With permission, approved feedback becomes a polished testimonial wall and "
            "embeddable website widget."
        ),
        "Choose your package and launch ReviewDesk for your business with Noerong.",
    ]
)


def font(size: int, semibold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_SEMIBOLD if semibold else FONT_REGULAR), size)


def rounded_panel(canvas: Image.Image, box: tuple[int, int, int, int], radius: int = 26) -> None:
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    x1, y1, x2, y2 = box
    shadow_draw.rounded_rectangle(
        (x1 + 8, y1 + 12, x2 + 8, y2 + 12), radius, fill=(0, 0, 0, 115)
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(canvas).rounded_rectangle(
        box, radius, fill=PANEL, outline="#33443D", width=2
    )


def brand_header(canvas: Image.Image, label: str) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((48, 28, 88, 68), 12, fill=ORANGE)
    draw.text((60, 33), "R", font=font(24, True), fill="#173029")
    draw.text((102, 31), "ReviewDesk", font=font(25, True), fill=CREAM)
    pill_width = draw.textbbox((0, 0), label.upper(), font=font(15, True))[2] + 34
    draw.rounded_rectangle(
        (WIDTH - 48 - pill_width, 32, WIDTH - 48, 64),
        16,
        fill="#182A24",
        outline="#365047",
    )
    draw.text(
        (WIDTH - 48 - pill_width + 17, 38),
        label.upper(),
        font=font(15, True),
        fill=MINT,
    )


def fit_scene(source: Path, target: Path, label: str, center_y: float = 0.5) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    brand_header(canvas, label)
    box = (38, 84, WIDTH - 38, HEIGHT - 34)
    rounded_panel(canvas, box)

    shot = Image.open(source).convert("RGB")
    fitted = ImageOps.fit(
        shot,
        (1168, 574),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, center_y),
    )
    x = (WIDTH - fitted.width) // 2
    y = 100
    mask = Image.new("L", fitted.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, fitted.width, fitted.height), 18, fill=255
    )
    canvas.paste(fitted, (x, y), mask)
    canvas.convert("RGB").save(target, quality=95)


def make_title(target: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(canvas)
    for x in range(0, WIDTH, 80):
        draw.line((x, 0, x, HEIGHT), fill="#12201B", width=1)
    for y in range(0, HEIGHT, 80):
        draw.line((0, y, WIDTH, y), fill="#12201B", width=1)

    draw.rounded_rectangle((70, 72, 116, 118), 14, fill=ORANGE)
    draw.text((84, 78), "R", font=font(26, True), fill="#173029")
    draw.text((132, 76), "REVIEWDESK", font=font(23, True), fill=CREAM)
    draw.rounded_rectangle((70, 175, 250, 215), 20, fill="#182A24", outline="#365047")
    draw.ellipse((89, 189, 101, 201), fill=MINT)
    draw.text((113, 183), "LIVE PRODUCT", font=font(16, True), fill=MINT)

    draw.text((70, 255), "Turn completed work", font=font(58, True), fill=CREAM)
    draw.text((70, 323), "into customer trust.", font=font(58, True), fill=ORANGE)
    draw.text(
        (72, 421),
        "Honest feedback, smart reminders, and permissioned testimonials",
        font=font(27),
        fill=MUTED,
    )

    pills = ["REVIEW REQUESTS", "FEEDBACK", "TESTIMONIALS"]
    x = 70
    for pill in pills:
        width = draw.textbbox((0, 0), pill, font=font(15, True))[2] + 38
        draw.rounded_rectangle(
            (x, 512, x + width, 552), 20, fill=PANEL, outline="#365047"
        )
        draw.text((x + 19, 520), pill, font=font(15, True), fill="#D7E0DB")
        x += width + 14

    canvas.convert("RGB").save(target, quality=95)


def make_workflow(target: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    brand_header(canvas, "AUTOMATED WORKFLOW")
    draw = ImageDraw.Draw(canvas)
    draw.text((62, 112), "A fair request flow from job to proof", font=font(38, True), fill=CREAM)
    draw.text(
        (64, 164),
        "Every customer gets the same path. Reminders stop after a response.",
        font=font(22),
        fill=MUTED,
    )

    cards = [
        ("01", "REQUEST", "Send after service", "#1F473F"),
        ("02", "LISTEN", "Capture honest feedback", "#273F38"),
        ("03", "REMIND", "Follow up on schedule", "#3C352B"),
        ("04", "SHARE", "Publish with permission", "#423127"),
    ]
    x = 62
    for number, title, copy, color in cards:
        box = (x, 244, x + 272, 492)
        draw.rounded_rectangle(box, 24, fill=color, outline="#496057", width=2)
        draw.rounded_rectangle((x + 22, 267, x + 72, 317), 16, fill="#0E1714")
        draw.text((x + 37, 278), number, font=font(17, True), fill=ORANGE)
        draw.text((x + 22, 354), title, font=font(22, True), fill=CREAM)
        draw.text((x + 22, 401), copy, font=font(17), fill="#C3CDC7")
        if x < 900:
            draw.text((x + 285, 345), "→", font=font(34, True), fill="#688078")
        x += 302

    draw.rounded_rectangle((62, 552, 1218, 628), 22, fill="#12201B", outline="#31483F")
    draw.ellipse((86, 579, 100, 593), fill=MINT)
    draw.text(
        (118, 571),
        "POLICY-SAFE: the public review option is available regardless of rating",
        font=font(19, True),
        fill="#DDE8E1",
    )
    canvas.convert("RGB").save(target, quality=95)


def make_outro(target: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((920, -140, 1320, 260), fill="#243C34")
    draw.ellipse((-160, 520, 240, 920), fill="#3C2C20")

    draw.rounded_rectangle((70, 70, 116, 116), 14, fill=ORANGE)
    draw.text((84, 76), "R", font=font(26, True), fill="#173029")
    draw.text((132, 74), "REVIEWDESK", font=font(23, True), fill=CREAM)

    draw.text((70, 213), "Build trust from", font=font(58, True), fill=CREAM)
    draw.text((70, 281), "every completed job.", font=font(58, True), fill=ORANGE)
    draw.text(
        (72, 388),
        "Review requests  •  Feedback  •  Reminders  •  Testimonial widget",
        font=font(27),
        fill=MUTED,
    )

    draw.rounded_rectangle((70, 490, 470, 558), 34, fill=MINT)
    draw.text(
        (108, 507),
        "CHOOSE A PACKAGE TO START",
        font=font(20, True),
        fill="#102016",
    )
    draw.text((70, 594), "Built by Noerong", font=font(19, True), fill="#DCE5E0")
    canvas.convert("RGB").save(target, quality=95)


async def create_narration() -> None:
    communicator = edge_tts.Communicate(
        NARRATION_TEXT,
        voice=VOICE,
        rate="-10%",
        volume="+0%",
        boundary="SentenceBoundary",
    )
    subtitle_maker = edge_tts.SubMaker()
    with NARRATION.open("wb") as audio_file:
        async for message in communicator.stream():
            if message["type"] == "audio":
                audio_file.write(message["data"])
            elif message["type"] == "SentenceBoundary":
                subtitle_maker.feed(message)
    SUBTITLES.write_text(subtitle_maker.get_srt(), encoding="utf-8")


def render_video() -> Path:
    asyncio.run(create_narration())

    title = FRAMES / "00-title.png"
    customer = FRAMES / "01-customer.png"
    dashboard = FRAMES / "02-dashboard.png"
    workflow = FRAMES / "03-workflow.png"
    wall = FRAMES / "04-wall.png"
    outro = FRAMES / "05-outro.png"

    make_title(title)
    fit_scene(ASSETS / "01-customer-feedback.png", customer, "BRANDED FEEDBACK")
    fit_scene(ASSETS / "02-review-dashboard.png", dashboard, "REVIEW DASHBOARD", 0.42)
    make_workflow(workflow)
    fit_scene(ASSETS / "03-testimonial-wall.png", wall, "TESTIMONIAL WALL")
    make_outro(outro)

    scenes = [
        (title, 4.0),
        (customer, 8.0),
        (dashboard, 8.5),
        (workflow, 7.5),
        (wall, 7.5),
        (outro, 8.0),
    ]

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-y"]
    for path, duration in scenes:
        command.extend(["-loop", "1", "-t", f"{duration:.1f}", "-i", str(path)])
    command.extend(["-i", str(NARRATION)])

    filters: list[str] = []
    for index, (_, duration) in enumerate(scenes):
        fade_out = max(duration - 0.25, 0)
        filters.append(
            f"[{index}:v]fps=30,format=yuv420p,"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.2f}:d=0.25,"
            f"setpts=PTS-STARTPTS[v{index}]"
        )
    joined = "".join(f"[v{i}]" for i in range(len(scenes)))
    filters.append(f"{joined}concat=n={len(scenes)}:v=1:a=0[base]")
    subtitle_path = SUBTITLES.relative_to(WORKSPACE).as_posix()
    filters.append(
        "[base]subtitles=filename='"
        + subtitle_path
        + "':force_style='FontName=Segoe UI,FontSize=16,PrimaryColour=&H00FFFFFF,"
        "BackColour=&H78000000,OutlineColour=&H78000000,BorderStyle=3,Outline=1,"
        "Shadow=0,MarginL=90,MarginR=90,MarginV=18,Alignment=2'[vout]"
    )
    audio_index = len(scenes)
    filters.append(f"[{audio_index}:a]apad=pad_dur=3[aout]")

    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-t",
            "44.0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-r",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(OUTPUT),
        ]
    )
    subprocess.run(command, cwd=WORKSPACE, check=True)
    return OUTPUT


if __name__ == "__main__":
    print(render_video())
