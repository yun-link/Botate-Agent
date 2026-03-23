import io
import json
import uuid
import os
import base64
import subprocess
import tempfile

from volcenginesdkarkruntime import Ark
import requests

from PIL import Image

client = Ark(
    api_key=os.getenv('VOLCENGINE_API_KEY')
)

def _to_base64(path, max_size_mb=10, max_pixels=3600000):
    with open(path, "rb") as file:
        data = file.read()
    
    max_bytes = max_size_mb * 1024 * 1024
    if len(data) <= max_bytes:
        return base64.b64encode(data).decode('utf-8')
    
    try:
        img = Image.open(io.BytesIO(data))
        
        width, height = img.size
        current_pixels = width * height
        
        if current_pixels > max_pixels:
            scale = (max_pixels / current_pixels) ** 0.5
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        quality = 90
        output = io.BytesIO()
        
        while True:
            output.seek(0)
            output.truncate(0)
            img.save(output, format=img.format or 'JPEG', quality=quality, optimize=True)
            
            if output.tell() <= max_bytes or quality <= 10:
                break
            quality -= 10
        
        return base64.b64encode(output.getvalue()).decode('utf-8')
        
    except Exception:
        return base64.b64encode(data[:max_bytes]).decode('utf-8')

def _audio_to_text(content, length):
    url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
    api_key = os.getenv('VOLCENGINE_API_KEY')
    payload = {
        "audio": {
            'data': content,
        },
        "request": {
            "model_name": "bigmodel"
        }
    }
       
    headers = {
        "Content-Type": "application/json",
        "x-api-key": '03674e4d-a637-4cc7-9e2b-1afa4f2167f9',
        "X-Api-Resource-Id": "volc.seedasr.auc",
        "X-Api-Request-Id": "a444b46c-f51d-44d6-8b09-b4a31ec44690",
        "X-Api-Sequence": "-1"
    }
    request = requests.post(url=url, json=payload, headers=headers)
    if request.status_code == 200:
        return request.json()['result']['text']
    else:
        return request.text