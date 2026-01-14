from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re
from urllib.parse import urlparse
import tempfile
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Frontend ekata access denna

# Temporary files wala tika save karanna
DOWNLOAD_FOLDER = tempfile.gettempdir()

def is_valid_url(url):
    """URL eka valid da kiyala check karanawa"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_platform(url):
    """URL eken platform eka identify karanawa"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'tiktok.com' in url:
        return 'tiktok'
    elif 'facebook.com' in url or 'fb.watch' in url:
        return 'facebook'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    else:
        return 'unknown'

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Video eke details gannawa (title, thumbnail, duration, available qualities)"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url or not is_valid_url(url):
            return jsonify({'error': 'Invalid URL'}), 400
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Available formats eka gannawa
            formats = []
            if info.get('formats'):
                seen_qualities = set()
                for f in info['formats']:
                    if f.get('height') and f.get('ext') in ['mp4', 'webm']:
                        quality = f"{f['height']}p"
                        if quality not in seen_qualities:
                            formats.append({
                                'quality': quality,
                                'format': f.get('ext', 'mp4'),
                                'filesize': f.get('filesize', 0)
                            })
                            seen_qualities.add(quality)
            
            # MP3 option ekath ekatu karanawa
            formats.append({
                'quality': 'Audio Only',
                'format': 'mp3',
                'filesize': 0
            })
            
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'platform': get_platform(url),
                'formats': sorted(formats, key=lambda x: int(re.findall(r'\d+', x['quality'])[0]) if x['quality'] != 'Audio Only' else 0, reverse=True)
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    """Video eka download karanawa"""
    try:
        data = request.get_json()
        url = data.get('url')
        quality = data.get('quality', '1080p')
        format_type = data.get('format', 'mp4')
        
        if not url or not is_valid_url(url):
            return jsonify({'error': 'Invalid URL'}), 400
        
        # Download options configure karanawa
        filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format_type == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{filename}.%(ext)s'),
                'quiet': True,
            }
        else:
            # Quality anuwa format select karanawa
            height = int(re.findall(r'\d+', quality)[0]) if quality != 'best' else 1080
            
            ydl_opts = {
                'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{filename}.%(ext)s'),
                'merge_output_format': 'mp4',
                'quiet': True,
            }
        
        # Download karanawa
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Downloaded file eka hoyagannawa
            ext = 'mp3' if format_type == 'mp3' else 'mp4'
            file_path = os.path.join(DOWNLOAD_FOLDER, f'{filename}.{ext}')
            
            if os.path.exists(file_path):
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=f"{info.get('title', 'video')}.{ext}",
                    mimetype=f'{"audio" if ext == "mp3" else "video"}/{ext}'
                )
            else:
                return jsonify({'error': 'Download failed'}), 500
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Server eka wada karanawada kiyala check karanawa"""
    return jsonify({'status': 'ok', 'message': 'Server is running'})

if __name__ == '__main__':
    # Development mode eke run karanawa
    app.run(debug=True, host='0.0.0.0', port=5000)