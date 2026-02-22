from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import yt_dlp
import os
import threading
import json
import re
import time
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Конфигурация
DOWNLOAD_FOLDER = 'downloads'
ALLOWED_EXTENSIONS = {'mp4', 'mp3', 'webm', 'm4a'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB max

# Создаем папки
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Хранилище прогресса и задач
downloads_progress = {}
active_downloads = {}

def sanitize_filename(filename):
    """Очистка имени файла от недопустимых символов"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename[:100]  # Ограничение длины

def format_bytes(bytes_value):
    """Форматирование байтов в читаемый вид"""
    if bytes_value is None or bytes_value == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_value) < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def format_duration(seconds):
    """Форматирование секунд в читаемый вид"""
    if not seconds:
        return "00:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def progress_hook(d, download_id):
    """Callback для отслеживания прогресса"""
    if download_id not in downloads_progress:
        return
        
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        
        percent = (downloaded / total * 100) if total > 0 else 0
        
        speed = d.get('speed', 0)
        eta = d.get('eta', 0)
        
        downloads_progress[download_id].update({
            'status': 'downloading',
            'percent': round(percent, 1),
            'downloaded': format_bytes(downloaded),
            'total': format_bytes(total),
            'speed': format_bytes(speed) + '/s' if speed else '0 B/s',
            'eta': format_duration(eta) if eta else 'calculating...',
            'filename': os.path.basename(d.get('filename', ''))
        })
        
    elif d['status'] == 'finished':
        downloads_progress[download_id].update({
            'status': 'processing',
            'percent': 100,
            'message': 'Обработка файла...'
        })

def get_video_info_sync(url):
    """Синхронное получение информации о видео"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except Exception as e:
            raise Exception(f"Не удалось получить информацию: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_video_info():
    """Получение информации о видео или плейлисте"""
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'URL не предоставлен'}), 400
    
    # Проверка валидности URL
    if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$', url):
        return jsonify({'error': 'Неверный URL YouTube'}), 400
    
    try:
        info = get_video_info_sync(url)
        
        # Проверяем, это плейлист или одно видео
        if 'entries' in info:
            # Это плейлист
            entries = list(info['entries'])[:50]  # Лимит 50 видео
            videos = []
            
            for entry in entries:
                if entry:
                    videos.append({
                        'id': entry.get('id'),
                        'title': entry.get('title', 'Unknown'),
                        'duration': entry.get('duration', 0),
                        'thumbnail': entry.get('thumbnail', ''),
                        'uploader': entry.get('uploader', 'Unknown')
                    })
            
            return jsonify({
                'type': 'playlist',
                'title': info.get('title', 'Playlist'),
                'uploader': info.get('uploader', 'Unknown'),
                'count': len(videos),
                'videos': videos
            })
        else:
            # Это одно видео
            formats_video = []
            formats_audio = []
            
            # Видео форматы (с аудио)
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    formats_video.append({
                        'format_id': f['format_id'],
                        'ext': f['ext'],
                        'quality': f.get('quality_label') or f"{f.get('height', 'unknown')}p",
                        'resolution': f"{f.get('width', '?')}x{f.get('height', '?')}",
                        'filesize': f.get('filesize') or f.get('filesize_approx', 0),
                        'filesize_str': format_bytes(f.get('filesize') or f.get('filesize_approx', 0))
                    })
            
            # Аудио форматы
            for f in info.get('formats', []):
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    formats_audio.append({
                        'format_id': f['format_id'],
                        'ext': f['ext'],
                        'abr': f.get('abr', 0),
                        'quality': f"{f.get('abr', '?')}kbps",
                        'filesize': f.get('filesize') or f.get('filesize_approx', 0),
                        'filesize_str': format_bytes(f.get('filesize') or f.get('filesize_approx', 0))
                    })
            
            # Сортируем по качеству
            formats_video.sort(key=lambda x: int(str(x['quality']).replace('p', '').replace('k', '')) if str(x['quality']).replace('p', '').replace('k', '').isdigit() else 0, reverse=True)
            formats_audio.sort(key=lambda x: x.get('abr', 0), reverse=True)
            
            # Убираем дубликаты качества
            seen_qualities = set()
            unique_formats = []
            for f in formats_video:
                if f['quality'] not in seen_qualities:
                    seen_qualities.add(f['quality'])
                    unique_formats.append(f)
            
            return jsonify({
                'type': 'video',
                'id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration', 0),
                'duration_str': format_duration(info.get('duration', 0)),
                'uploader': info.get('uploader'),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count'),
                'formats_video': unique_formats[:6],
                'formats_audio': formats_audio[:4]
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download_video():
    """Начало загрузки видео"""
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id', 'best')
    download_type = data.get('type', 'video')  # video или audio
    filename_custom = data.get('filename', '')
    
    if not url:
        return jsonify({'error': 'URL не предоставлен'}), 400
    
    download_id = f"{int(time.time() * 1000)}_{os.urandom(4).hex()}"
    downloads_progress[download_id] = {
        'status': 'starting',
        'percent': 0,
        'created_at': datetime.now().isoformat()
    }
    
    def download_task():
        try:
            output_template = os.path.join(DOWNLOAD_FOLDER, f'{download_id}_%(title)s.%(ext)s')
            
            if download_type == 'audio':
                # Только аудио
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': output_template,
                    'progress_hooks': [lambda d: progress_hook(d, download_id)],
                    'quiet': True,
                    'no_warnings': True,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'prefer_ffmpeg': True,
                    'keepvideo': False,
                }
            else:
                # Видео
                if format_id == 'best':
                    ydl_opts = {
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'outtmpl': output_template,
                        'progress_hooks': [lambda d: progress_hook(d, download_id)],
                        'quiet': True,
                        'no_warnings': True,
                        'merge_output_format': 'mp4',
                    }
                else:
                    ydl_opts = {
                        'format': format_id,
                        'outtmpl': output_template,
                        'progress_hooks': [lambda d: progress_hook(d, download_id)],
                        'quiet': True,
                        'no_warnings': True,
                    }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(download_id)]
                
                if downloaded_files:
                    actual_filename = downloaded_files[0]
                    original_path = os.path.join(DOWNLOAD_FOLDER, actual_filename)
                    
                    # Переименовываем в читаемое имя
                    final_filename = sanitize_filename(info.get('title', 'video')) + os.path.splitext(actual_filename)[1]
                    final_path = os.path.join(DOWNLOAD_FOLDER, f"{download_id}_{final_filename}")
                    
                    os.rename(original_path, final_path)
                    
                    downloads_progress[download_id].update({
                        'status': 'completed',
                        'percent': 100,
                        'filename': final_filename,
                        'file_path': final_path,
                        'file_size': format_bytes(os.path.getsize(final_path))
                    })
                else:
                    raise Exception("Файл не найден после загрузки")
                    
        except Exception as e:
            downloads_progress[download_id].update({
                'status': 'error',
                'error': str(e)
            })
    
    thread = threading.Thread(target=download_task)
    thread.start()
    active_downloads[download_id] = thread
    
    return jsonify({
        'download_id': download_id,
        'status': 'started'
    })

@app.route('/api/progress/<download_id>')
def get_progress(download_id):
    """Получение прогресса загрузки"""
    progress = downloads_progress.get(download_id, {
        'status': 'not_found',
        'error': 'Загрузка не найдена'
    })
    return jsonify(progress)

@app.route('/api/download/file/<download_id>')
def download_file(download_id):
    """Скачивание готового файла"""
    progress = downloads_progress.get(download_id, {})
    
    if progress.get('status') != 'completed':
        return jsonify({'error': 'Файл еще не готов'}), 400
    
    file_path = progress.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Файл не найден'}), 404
    
    filename = progress.get('filename', 'video.mp4')
    
    @after_this_request
    def cleanup(response):
        # Удаляем файл через 1 минуту после отправки
        def delayed_remove():
            time.sleep(60)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    del downloads_progress[download_id]
            except:
                pass
        threading.Thread(target=delayed_remove).start()
        return response
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )

@app.route('/api/cancel/<download_id>', methods=['POST'])
def cancel_download(download_id):
    """Отмена загрузки"""
    if download_id in active_downloads:
        # Помечаем для отмены (полная остановка потока сложна)
        downloads_progress[download_id]['status'] = 'cancelled'
        return jsonify({'status': 'cancelled'})
    return jsonify({'error': 'Загрузка не найдена'}), 404

@app.route('/api/history')
def get_history():
    """Получение истории загрузок"""
    completed = []
    for did, data in downloads_progress.items():
        if data.get('status') == 'completed':
            completed.append({
                'id': did,
                'filename': data.get('filename'),
                'size': data.get('file_size'),
                'date': data.get('created_at')
            })
    return jsonify(completed[-10:])  # Последние 10

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)