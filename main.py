from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import tempfile
import os
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap

app = FastAPI()

# --------- AUDIO FUNCTION ---------
def audio(data):
    api_url = "https://voice-nt6p.onrender.com/speak"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio_file:
            tmp_audio_file.write(response.content)
            return tmp_audio_file.name

    except Exception as e:
        print("Audio error:", e)
        return None

# --------- TEXT WRAPPING ---------
def wrap_text(text, font, draw, max_width):
    wrapped_lines = []
    for line in text.split('\n'):
        words = line.split()
        if not words:
            wrapped_lines.append('')
            continue

        current_line = words[0]
        for word in words[1:]:
            trial_line = f"{current_line} {word}"
            bbox = draw.textbbox((0, 0), trial_line, font=font)
            text_width = bbox[2] - bbox[0]
            if text_width <= max_width:
                current_line = trial_line
            else:
                wrapped_lines.append(current_line)
                current_line = word
        wrapped_lines.append(current_line)
    return wrapped_lines

# --------- REQUEST BODY ---------
class TextPayload(BaseModel):
    english: dict
    hindi: dict

# --------- API ENDPOINT ---------
@app.post("/generate-video")
def generate_video(payload: TextPayload):
    english = payload.english
    hindi = payload.hindi

    width, height = 480, 720
    font_size = 36
    duration = 5  # fallback
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "one.ttf")

    # AUDIO
    english_audio_path = audio(english)
    hindi_audio_path = audio(hindi)

    if not english_audio_path or not hindi_audio_path:
        return {"error": "Failed to generate audio"}

    audio_clips = [AudioFileClip(english_audio_path), AudioFileClip(hindi_audio_path)]
    final_audio = concatenate_audioclips(audio_clips)
    duration = final_audio.duration

    # TEXT
  #  text = f"{english['text']}\n-----------\n``````````\n{hindi['text']}"
    #image = Image.new("RGB", (width, height), color=(245, 245, 240))  # soft off-white
   # draw = ImageDraw.Draw(image)
  #  font = ImageFont.truetype(font_path, font_size)


     # TEXT
    text = f"{english['text']}\n-----------\n``````````\n{hindi['text']}"

# Gradient background (left-to-right: #00C6FF → #E61EAD)
    start_color = (0, 198, 255)   # #00C6FF
    end_color = (230, 30, 173)    # #E61EAD
    image = Image.new("RGB", (width, height), color=0)
    for x in range(width):
     blend = x / (width - 1)
     r = int(start_color[0] * (1 - blend) + end_color[0] * blend)
     g = int(start_color[1] * (1 - blend) + end_color[1] * blend)
     b = int(start_color[2] * (1 - blend) + end_color[2] * blend)
    for y in range(height):
     image.putpixel((x, y), (r, g, b))

# Draw inner black rectangle (like screenshot border effect)
    margin = 5
    draw = ImageDraw.Draw(image)
    draw.rectangle([margin, margin, width - margin, height - margin],outline=None,fill=(0, 0, 0))

# Now prepare font
    font = ImageFont.truetype(font_path, font_size)
    max_text_width = width - 100
    lines = wrap_text(text, font, draw, max_text_width)
    line_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines]
    total_text_height = sum(line_heights)
    start_y = (height - total_text_height) / 2

    y_offset = 0
    for line, line_height in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) / 2
        draw.text((x, start_y + y_offset), line, fill="white", font=font)
        y_offset += line_height

    image_np = np.array(image)
    bg_clip = ImageClip(image_np).set_duration(duration)
    video = bg_clip.set_audio(final_audio)

    output_path = os.path.join("static", "output_video.mp4")
    os.makedirs("static", exist_ok=True)
    video.write_videofile(output_path, fps=12)

    # CLEANUP
    os.remove(english_audio_path)
    os.remove(hindi_audio_path)

    return FileResponse(output_path, media_type="video/mp4", filename="output_video.mp4")
