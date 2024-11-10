from flask import Flask, render_template, jsonify
import csv
from urllib.parse import urlparse, parse_qs, unquote
import os
import requests
import base64
import re
import validators

app = Flask(__name__)

def decode_base64_url(url):
    """Decode base64 encoded URLs"""
    try:
        match = re.search(r'link=([^&]+)', url)
        if match:
            encoded_part = match.group(1)
            decoded_url = unquote(encoded_part)
            actual_url = base64.b64decode(decoded_url).decode('utf-8')
            return actual_url
    except:
        return url
    return url

def get_first_youtube_video_url(search_url):
    """Extract the first video URL from YouTube search results"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(search_url, headers=headers)
        video_id_pattern = r'watch\?v=([a-zA-Z0-9_-]+)'
        match = re.search(video_id_pattern, response.text)
        
        if match:
            video_id = match.group(1)
            return f'https://www.youtube.com/watch?v={video_id}'
    except:
        return None
    return None

def extract_spotify_uri(url):
    """Extract Spotify track/album/playlist ID from URL"""
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        if len(path_parts) >= 3:
            return f"{path_parts[-2]}/{path_parts[-1]}"
    except:
        pass
    return None

def get_media_type(url):
    """Determine media type and get appropriate embed URL"""
    if not url or not validators.url(url):
        return {
            'type': 'error',
            'message': 'Invalid or empty URL'
        }
        
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Handle YouTube
        if 'youtube.com' in domain or 'youtu.be' in domain:
            # Check if it's a search results page
            if 'results' in parsed_url.path:
                actual_video_url = get_first_youtube_video_url(url)
                if actual_video_url:
                    url = actual_video_url
                    parsed_url = urlparse(url)
                else:
                    return {
                        'type': 'error',
                        'message': 'Could not find video in search results'
                    }

            video_id = None
            if 'youtube.com' in domain:
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            elif 'youtu.be' in domain:
                video_id = parsed_url.path[1:]
            
            if video_id:
                return {
                    'type': 'youtube',
                    'embed_url': f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1",
                    'video_id': video_id  # Adding video_id for API control
                }
        
        # Handle Dailymotion
        elif 'dailymotion.com' in domain:
            video_id = parsed_url.path.split('/')[-1].split('_')[0]
            return {
                'type': 'dailymotion',
                'embed_url': f"https://www.dailymotion.com/embed/video/{video_id}?autoplay=1&api=1",
                'video_id': video_id
            }
            
        # Handle SoundCloud
        elif 'soundcloud.com' in domain:
            return {
                'type': 'soundcloud',
                'embed_url': f"https://w.soundcloud.com/player/?url={url}&auto_play=true&color=%23ff5500&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true&visual=true&api=1"
            }
        
        # Handle Spotify
        elif 'spotify.com' in domain:
            spotify_uri = extract_spotify_uri(url)
            if spotify_uri:
                return {
                    'type': 'spotify',
                    'embed_url': f"https://open.spotify.com/embed/{spotify_uri}"
                }
        
        # Handle Vimeo
        elif 'vimeo.com' in domain:
            video_id = parsed_url.path.split('/')[-1]
            return {
                'type': 'vimeo',
                'embed_url': f"https://player.vimeo.com/video/{video_id}?autoplay=1&api=1",
                'video_id': video_id
            }

        # Try to detect content type for direct media files
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Range': 'bytes=0-0'
            }
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
            content_type = response.headers.get('content-type', '').lower()
            
            # Handle direct audio files
            if 'audio' in content_type or any(ext in url.lower() for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
                return {
                    'type': 'audio',
                    'url': url
                }
            
            # Handle direct video files
            elif 'video' in content_type or any(ext in url.lower() for ext in ['.mp4', '.webm', '.mov']):
                return {
                    'type': 'video',
                    'url': url
                }
                
        except requests.exceptions.RequestException:
            if any(ext in url.lower() for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
                return {
                    'type': 'audio',
                    'url': url
                }
            elif any(ext in url.lower() for ext in ['.mp4', '.webm', '.mov']):
                return {
                    'type': 'video',
                    'url': url
                }
        
        return {
            'type': 'unknown',
            'original_url': url,
            'message': 'Unsupported media format or URL'
        }
        
    except Exception as e:
        return {
            'type': 'error',
            'original_url': url,
            'message': str(e)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_songs')
def load_songs():
    songs = []
    try:
        with open('songs.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                url = row.get('URL', '').strip()
                if url:  # Only process non-empty URLs
                    media_info = get_media_type(url)
                    row.update(media_info)
                    songs.append(row)
    except Exception as e:
        print(f"Error loading songs: {e}")
        return jsonify({"error": str(e)}), 500
    return jsonify(songs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
