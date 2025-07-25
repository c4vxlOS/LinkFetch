from flask import Flask, request, jsonify, Response, stream_with_context
import requests
import argparse
import os
import re
from yt_dlp import YoutubeDL
import uuid
import subprocess
import mimetypes

FILE_SERVER_INSTANCE = None

def get_media_info(url: str):
    with YoutubeDL({
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }) as ydl:
        try:
            return ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"[yt_dlp] Extraction failed: {e}")
            return None

def get_media_data(url: str):
    info = get_media_info(url)

    if not info:
        return None

    formats = info.get("formats", [])

    # Filter formats
    video_formats = sorted(
                [ f for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("height") is not None ],
                key=lambda f: f["height"], reverse=True
    )
    audio_formats = sorted(
                [ f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none" and f.get("abr") is not None ],
                key=lambda f: f["abr"], reverse=True
    )

    def pick(type, formats):
        count = len(formats)
        if count == 0:
            return []
        
        labels = { 1: ["high"], 2: ["high", "low"] }.get(count, ["high", "medium", "low"])
        
        picked = []
        indices = { "high": 0, "medium": count // 2, "low": count - 1 }
        
        def safename(name: str) -> str:
            return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', name).strip()
        
        for label in labels:
            fmt = formats[indices[label]]
            extension = fmt.get("ext") or fmt.get("format").split()[0]
            
            picked = picked + [{
                "type": type,
                "quality": label,
                "format": fmt["format"],
                "url": fmt["url"],
                "filename": safename(f"{info.get('title', 'unknown')} ({label}).{extension}"),
                "extension": extension
            }]

        return picked

    return {
        "thumbnail": info.get("thumbnail"),
        "title": info.get("title"),
        "formats": pick("video", video_formats) + pick("audio", audio_formats),
        "src": url
    }

def stream_muxed(url: str, f: str = "mp4"):
    process = subprocess.Popen(
        ["ffmpeg", "-i", url, "-f", f, "-movflags", "frag_keyframe+empty_moov", "pipe:1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=10**5
    )

    def generate():
        while True:
            chunk = process.stdout.read(1024 * 64)
            if not chunk:
                break
            yield chunk

    return generate()

def get_template(name):
    return open(os.path.dirname(os.path.abspath(__file__)) + "/" + name + ".template", "r").read()

def create_flask_server():
    app = Flask(__name__)

    @app.route("/")
    def _root():
        return get_template("index")
    
    @app.route("/fetch/<path:url>")
    def _fetch(url):
        args = "&".join(f"{k}={v}" for k, v in request.args.to_dict().items())
        if args:
            url += f"?{args}"

        return jsonify(get_media_data(url))

    @app.route("/fileserver")
    def _fileserver():
        return jsonify(FILE_SERVER_INSTANCE)
    
    @app.route("/direct_stream/<path:url>")
    def _direct_stream(url):
        if not url:
            return jsonify({"success": False, "error": "Invalid url!"})

        args = "&".join(f"{k}={v}" for k, v in request.args.to_dict().items())
        if args:
            url += f"?{args}"

        info = get_media_info(url)
        if not info:
            return jsonify({"success": False, "error": "Failed to fetch!"})

        format = "mp4" if any(
            f.get("vcodec") != "none" and f.get("acodec") != "none"
            for f in info.get("formats", [])
        ) else "mp3"

        return Response(stream_with_context(stream_muxed(url, format)), mimetype="video/mp4" if format == "mp4" else "audio/mp3")

    @app.route("/stream/<type>/<quality>/<path:url>")
    def _stream(type, quality, url):
        if not url:
            return jsonify({"success": False, "error": "Invalid url!"})

        args = "&".join(f"{k}={v}" for k, v in request.args.to_dict().items())
        if args:
            url += f"?{args}"

        data = get_media_data(url)

        format = None
        for f in data["formats"]:
            if f["type"] == type and f["quality"] == quality:
                format = f
                break
        
        if not format:
            return jsonify({"success": False, "error": f"Failed to find {type}!"})

        return _direct_stream(format["url"])

    @app.route("/export_fileserver", methods=["POST"])
    def _export_fileserver():
        json = dict(request.get_json())
        url = json.get("url", None)
        instance = json.get("instance", FILE_SERVER_INSTANCE)
        instance = instance.replace("__self__", f"{request.scheme}://{request.host.split(':')[0]}").removesuffix("/")
        id = json.get("id", str(uuid.uuid4()))
        filename = json.get("filename", url.split("/")[-1].split("?")[0].split("#")[0])

        if url == None:
            return jsonify({ "error": "No URL passed!", "success": False })
        
        if instance == None:
            return jsonify({ "error": "No FSI passed!", "success": False })
        
        try:
            download_response = requests.get(f"{'/'.join(request.url.split('/')[:-1])}/direct_stream/{url}", stream=True)
            if download_response.status_code != 200:
                return jsonify({ "error": "Failed to download the file!", "success": False })

            files = { "file": (filename, download_response.raw, download_response.headers.get("Content-Type", "application/octet-stream")) }

            upload_response = requests.post(f"{instance}/upload/{id}", files=files)

            if upload_response.status_code != 200:
                return jsonify({ "error": "Failed on FSI upload!", "success": False })

            return jsonify({ "success": True, "url": f"{instance}/{id}" })

        except Exception as e:
            return jsonify({ "error": "Server error: " + str(e), "success": False })

    return app

def start_flask_server(port = 4420, host = "127.0.0.1"):
    server = create_flask_server()
    server.run(host, port, False)    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Host a server synced version of mkgallery.")
    parser.add_argument("--port", "-po", type=int, help="Set the port the server should be running on. (Default: 4423)", default=4423)
    parser.add_argument("--host", "-ht", type=str, help="Set the host the server should be running on. (Default: 127.0.0.1)", default="127.0.0.1")
    parser.add_argument("--fileserver", "-fs", type=str, help="Set the url to a fileserver instance.")

    args = parser.parse_args()

    FILE_SERVER_INSTANCE  = args.fileserver

    start_flask_server(args.port, args.host)