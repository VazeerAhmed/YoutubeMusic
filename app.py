from flask import Flask, render_template, jsonify, send_from_directory
import csv
from urllib.parse import urlparse, parse_qs, unquote
import os
import requests
import base64
import re
import validators
from functools import lru_cache
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from concurrent.futures import ThreadPoolExecutor
import time
from collections import OrderedDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimedCache:
    def __init__(self, maxsize=100, ttl=3600):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        
    def __call__(self, func):
        def wrapped_func(*args, **kwargs):
            key = str(args) + str(kwargs)
            
            # Clear expired entries
            current_time = time.time()
            # Collect expired keys in a separate list
            expired_keys = [k for k, (_, timestamp) in list(self.cache.items()) 
                         if current_time - timestamp > self.ttl]
            # Remove each expired key without iterating over the OrderedDict directly
            for k in expired_keys:
                self.cache.pop(k, None)  # Use pop with default None to avoid KeyError

            # Check cache
            if key in self.cache:
                value, timestamp = self.cache[key]
                if current_time - timestamp <= self.ttl:
                    return value
                else:
                    self.cache.pop(key)
            
            # Compute new value
            result = func(*args, **kwargs)
            
            # Add to cache
            self.cache[key] = (result, current_time)
            
            # Remove oldest if cache is full
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)
                
            return result
        return wrapped_func

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Create a thread pool for concurrent operations
executor = ThreadPoolExecutor(max_workers=3)

@TimedCache(maxsize=100, ttl=3600)
def get_media_type_cached(url):
    """Cached version of media type detection"""
    return get_media_type(url)

def decode_base64_url(url):
    """Decode base64 encoded URLs with error handling"""
    try:
        match = re.search(r'link=([^&]+)', url)
        if match:
            encoded_part = match.group(1)
            decoded_url = unquote(encoded_part)
            actual_url = base64.b64decode(decoded_url).decode('utf-8')
            return actual_url
    except Exception as e:
        logger.error(f"Error decoding base64 URL: {e}")
        return url
    return url

@TimedCache(maxsize=50, ttl=1800)
def get_first_youtube_video_url(search_url):
    """Cached YouTube search results"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=5)
        video_id_pattern = r'watch\?v=([a-zA-Z0-9_-]+)'
        match = re.search(video_id_pattern, response.text)
        
        if match:
            video_id = match.group(1)
            return f'https://www.youtube.com/watch?v={video_id}'
    except Exception as e:
        logger.error(f"Error fetching YouTube video: {e}")
        return None
    return None

def extract_spotify_uri(url):
    """Extract Spotify URI with validation"""
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        if len(path_parts) >= 3 and all(part.strip() for part in path_parts[-2:]):
            return f"{path_parts[-2]}/{path_parts[-1]}"
    except Exception as e:
        logger.error(f"Error extracting Spotify URI: {e}")
    return None

def get_media_type(url):
    """Determine media type with improved error handling and validation"""
    if not url or not validators.url(url):
        return {
            'type': 'error',
            'message': 'Invalid or empty URL'
        }
        
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Handle different media types
        handlers = {
            'youtube.com': handle_youtube,
            'youtu.be': handle_youtube,
            'dailymotion.com': handle_dailymotion,
            'soundcloud.com': handle_soundcloud,
            'spotify.com': handle_spotify,
            'vimeo.com': handle_vimeo
        }
        
        for domain_key, handler in handlers.items():
            if domain_key in domain:
                return handler(parsed_url, url)
                
        # Handle direct media files
        return handle_direct_media(url)
        
    except Exception as e:
        logger.error(f"Error processing media type for URL {url}: {e}")
        return {
            'type': 'error',
            'original_url': url,
            'message': str(e)
        }

def handle_youtube(parsed_url, url):
    """Handle YouTube URLs"""
    if 'results' in parsed_url.path:
        actual_video_url = get_first_youtube_video_url(url)
        if actual_video_url:
            url = actual_video_url
            parsed_url = urlparse(url)
        else:
            return {'type': 'error', 'message': 'Could not find video'}

    video_id = None
    if 'youtube.com' in parsed_url.netloc:
        video_id = parse_qs(parsed_url.query).get('v', [None])[0]
    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path[1:]
    
    if video_id:
        return {
            'type': 'youtube',
            'embed_url': f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1",
            'video_id': video_id
        }
    return {'type': 'error', 'message': 'Invalid YouTube URL'}

def handle_dailymotion(parsed_url, url):
    """Handle Dailymotion URLs"""
    video_id = parsed_url.path.split('/')[-1].split('_')[0]
    return {
        'type': 'dailymotion',
        'embed_url': f"https://www.dailymotion.com/embed/video/{video_id}?autoplay=1&api=1",
        'video_id': video_id
    }

def handle_soundcloud(parsed_url, url):
    """Handle SoundCloud URLs"""
    return {
        'type': 'soundcloud',
        'embed_url': f"https://w.soundcloud.com/player/?url={url}&auto_play=true&color=%23ff5500&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true&visual=true&api=1"
    }

def handle_spotify(parsed_url, url):
    """Handle Spotify URLs"""
    spotify_uri = extract_spotify_uri(url)
    if spotify_uri:
        return {
            'type': 'spotify',
            'embed_url': f"https://open.spotify.com/embed/{spotify_uri}"
        }
    return {'type': 'error', 'message': 'Invalid Spotify URL'}

def handle_vimeo(parsed_url, url):
    """Handle Vimeo URLs"""
    video_id = parsed_url.path.split('/')[-1]
    return {
        'type': 'vimeo',
        'embed_url': f"https://player.vimeo.com/video/{video_id}?autoplay=1&api=1",
        'video_id': video_id
    }

def handle_direct_media(url):
    """Handle direct media file URLs"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Range': 'bytes=0-0'
        }
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
        content_type = response.headers.get('content-type', '').lower()
        
        if 'audio' in content_type or any(ext in url.lower() for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
            return {'type': 'audio', 'url': url}
        elif 'video' in content_type or any(ext in url.lower() for ext in ['.mp4', '.webm', '.mov']):
            return {'type': 'video', 'url': url}
            
    except requests.exceptions.RequestException:
        # Try to determine type from extension if request fails
        if any(ext in url.lower() for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
            return {'type': 'audio', 'url': url}
        elif any(ext in url.lower() for ext in ['.mp4', '.webm', '.mov']):
            return {'type': 'video', 'url': url}
    
    return {
        'type': 'unknown',
        'original_url': url,
        'message': 'Unsupported media format or URL'
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_songs')
def load_songs():
    songs = []
    try:
        # Use thread pool for concurrent processing
        with open('songs.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            
        def process_song(row):
            url = row.get('URL', '').strip()
            if url:
                media_info = get_media_type_cached(url)
                row.update(media_info)
                return row
            return None
            
        # Process songs concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            processed_songs = list(executor.map(process_song, rows))
            songs = [song for song in processed_songs if song is not None]
            
    except Exception as e:
        logger.error(f"Error loading songs: {e}")
        return jsonify({"error": str(e)}), 500
        
    return jsonify(songs)

# calling api from html file

# Add these constants at the top of your app.py
WEATHER_API_KEY = "1cc79e5a9915e18d74c8a0aa0002020a"
NEWS_API_KEY = "b4b41d797ab04b329ae41b7052e5db5c"

# Weather endpoint
@app.route('/api/weather', methods=['GET'])
def get_weather():
    lat = request.args.get('lat', default=None, type=float)
    lon = request.args.get('lon', default=None, type=float)

    if not lat or not lon:
        return jsonify({"error": "Latitude and longitude are required"}), 400

    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(weather_url, timeout=5)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return jsonify({"error": "Failed to fetch weather data"}), 500

# News endpoint
@app.route('/api/news', methods=['GET'])
def get_news():
    country = request.args.get('country', default='us', type=str)

    news_url = f"https://newsapi.org/v2/top-headlines?apiKey={NEWS_API_KEY}&country={country}"
    try:
        response = requests.get(news_url, timeout=5)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching news data: {e}")
        return jsonify({"error": "Failed to fetch news data"}), 500



if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
