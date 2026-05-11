from flask import Flask, jsonify, render_template, request
import random
import sqlite3
import requests
import json
import os
from datetime import datetime
import threading
import time

app = Flask(__name__)

# ==================== إعدادات التخزين السحابي ====================

# يمكنك استخدام أي خدمة تخزين سحابي
CLOUD_PROVIDER = os.environ.get('CLOUD_PROVIDER', 'github')  # github, dropbox, gist
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', 'your-github-token')
GITHUB_GIST_ID = os.environ.get('GITHUB_GIST_ID', 'your-gist-id')
DATABASE_FILE = 'gallery.db'
BACKUP_FILE = 'gallery_backup.db'

# ==================== نظام النسخ الاحتياطي السحابي ====================

class CloudSync:
    def __init__(self):
        self.sync_enabled = True
        self.last_sync = None
    
    def save_to_cloud(self, db_path):
        """حفظ قاعدة البيانات إلى السحابة"""
        try:
            if CLOUD_PROVIDER == 'github':
                return self._save_to_github_gist(db_path)
            elif CLOUD_PROVIDER == 'dropbox':
                return self._save_to_dropbox(db_path)
            else:
                # حفظ محلي مع نسخة احتياطية
                return self._save_local_backup(db_path)
        except Exception as e:
            print(f"Cloud sync error: {e}")
            return self._save_local_backup(db_path)
    
    def _save_to_github_gist(self, db_path):
        """حفظ قاعدة البيانات إلى GitHub Gist"""
        try:
            with open(db_path, 'rb') as f:
                content = f.read()
                # تحويل المحتوى إلى base64
                import base64
                encoded_content = base64.b64encode(content).decode()
            
            headers = {
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            data = {
                'description': f'Gallery Database Backup - {datetime.now().isoformat()}',
                'public': False,
                'files': {
                    'gallery.db': {
                        'content': encoded_content,
                        'encoding': 'base64'
                    }
                }
            }
            
            # تحديث الـ Gist إذا كان موجوداً
            if GITHUB_GIST_ID and GITHUB_GIST_ID != 'your-gist-id':
                response = requests.patch(
                    f'https://api.github.com/gists/{GITHUB_GIST_ID}',
                    headers=headers,
                    json=data
                )
            else:
                # إنشاء Gist جديد
                response = requests.post(
                    'https://api.github.com/gists',
                    headers=headers,
                    json=data
                )
                if response.status_code == 201:
                    new_gist_id = response.json().get('id')
                    print(f"New Gist created! Update your GITHUB_GIST_ID to: {new_gist_id}")
            
            if response.status_code in [200, 201]:
                self.last_sync = datetime.now()
                print(f"✓ Cloud sync successful at {self.last_sync}")
                return True
            else:
                print(f"GitHub API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"GitHub sync failed: {e}")
            return False
    
    def _save_to_dropbox(self, db_path):
        """حفظ إلى Dropbox"""
        try:
            DROPBOX_TOKEN = os.environ.get('DROPBOX_TOKEN')
            with open(db_path, 'rb') as f:
                headers = {
                    'Authorization': f'Bearer {DROPBOX_TOKEN}',
                    'Dropbox-API-Arg': json.dumps({
                        'path': '/gallery.db',
                        'mode': 'overwrite'
                    }),
                    'Content-Type': 'application/octet-stream'
                }
                response = requests.post(
                    'https://content.dropboxapi.com/2/files/upload',
                    headers=headers,
                    data=f
                )
                if response.status_code == 200:
                    self.last_sync = datetime.now()
                    print(f"✓ Dropbox sync successful")
                    return True
        except Exception as e:
            print(f"Dropbox sync failed: {e}")
        return False
    
    def _save_local_backup(self, db_path):
        """نسخ احتياطي محلي"""
        try:
            import shutil
            shutil.copy2(db_path, BACKUP_FILE)
            print(f"✓ Local backup created")
            return True
        except Exception as e:
            print(f"Local backup failed: {e}")
            return False
    
    def load_from_cloud(self, db_path):
        """تحميل قاعدة البيانات من السحابة"""
        try:
            if CLOUD_PROVIDER == 'github':
                return self._load_from_github_gist(db_path)
            elif CLOUD_PROVIDER == 'dropbox':
                return self._load_from_dropbox(db_path)
            return False
        except Exception as e:
            print(f"Cloud load error: {e}")
            return False
    
    def _load_from_github_gist(self, db_path):
        """تحميل من GitHub Gist"""
        try:
            if not GITHUB_GIST_ID or GITHUB_GIST_ID == 'your-gist-id':
                return False
                
            headers = {
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(
                f'https://api.github.com/gists/{GITHUB_GIST_ID}',
                headers=headers
            )
            
            if response.status_code == 200:
                gist_data = response.json()
                if 'gallery.db' in gist_data.get('files', {}):
                    import base64
                    content = gist_data['files']['gallery.db'].get('content', '')
                    if content:
                        with open(db_path, 'wb') as f:
                            f.write(base64.b64decode(content))
                        print("✓ Database loaded from Gist")
                        return True
            return False
        except Exception as e:
            print(f"GitHub load failed: {e}")
            return False
    
    def _load_from_dropbox(self, db_path):
        """تحميل من Dropbox"""
        try:
            DROPBOX_TOKEN = os.environ.get('DROPBOX_TOKEN')
            headers = {
                'Authorization': f'Bearer {DROPBOX_TOKEN}',
                'Dropbox-API-Arg': json.dumps({'path': '/gallery.db'})
            }
            response = requests.post(
                'https://content.dropboxapi.com/2/files/download',
                headers=headers
            )
            if response.status_code == 200:
                with open(db_path, 'wb') as f:
                    f.write(response.content)
                print("✓ Database loaded from Dropbox")
                return True
        except Exception as e:
            print(f"Dropbox load failed: {e}")
        return False

# ==================== قاعدة البيانات مع المزامنة ====================

cloud_sync = CloudSync()

class DatabaseManager:
    def __init__(self, db_path='gallery.db'):
        self.db_path = db_path
        self.local = threading.local()
    
    def get_connection(self):
        """الحصول على اتصال بقاعدة البيانات"""
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            self.local.conn = sqlite3.connect(self.db_path)
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn
    
    def close_connection(self):
        """إغلاق الاتصال"""
        if hasattr(self.local, 'conn') and self.local.conn:
            self.local.conn.close()
            self.local.conn = None
    
    def sync_to_cloud(self):
        """مزامنة إلى السحابة"""
        try:
            # تأكد من حفظ جميع التغييرات
            if hasattr(self.local, 'conn') and self.local.conn:
                self.local.conn.commit()
            
            # رفع إلى السحابة
            cloud_sync.save_to_cloud(self.db_path)
        except Exception as e:
            print(f"Sync error: {e}")

db_manager = DatabaseManager()

# ==================== دوال قاعدة البيانات ====================

def init_db():
    """تهيئة قاعدة البيانات"""
    # محاولة تحميل من السحابة أولاً
    cloud_sync.load_from_cloud(DATABASE_FILE)
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الصور المحفوظة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            photo_url TEXT NOT NULL,
            photo_id INTEGER,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # جدول عمليات البحث
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            search_query TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # جدول الإحصائيات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_name TEXT UNIQUE,
            stat_value INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # إنشاء نسخة احتياطية أولية
    cloud_sync.save_to_cloud(DATABASE_FILE)
    
    print("✓ Database initialized successfully")

# دوال المستخدمين
def add_user(name, email, phone):
    """إضافة مستخدم جديد"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (name, email, phone) VALUES (?, ?, ?)',
            (name, email, phone)
        )
        conn.commit()
        update_stat('total_users')
        db_manager.sync_to_cloud()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"Add user error: {e}")
        return False

def get_user_by_email(email):
    """البحث عن مستخدم بالبريد الإلكتروني"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    return user

def get_all_users():
    """الحصول على جميع المستخدمين"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY id DESC')
    users = cursor.fetchall()
    return users

def get_user_by_id(user_id):
    """البحث عن مستخدم بالمعرف"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    return user

# دوال الصور
def save_photo(user_id, photo_url, photo_id=None, title=''):
    """حفظ صورة"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO photos (user_id, photo_url, photo_id, title) VALUES (?, ?, ?, ?)',
            (user_id, photo_url, photo_id, title)
        )
        conn.commit()
        update_stat('total_saved_photos')
        db_manager.sync_to_cloud()
        return True
    except Exception as e:
        print(f"Save photo error: {e}")
        return False

def get_saved_photos(user_id=None):
    """الحصول على الصور المحفوظة"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute(
            'SELECT * FROM photos WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        )
    else:
        cursor.execute('SELECT * FROM photos ORDER BY created_at DESC')
    photos = cursor.fetchall()
    return photos

def delete_photo(photo_id, user_id):
    """حذف صورة"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'DELETE FROM photos WHERE id = ? AND user_id = ?',
            (photo_id, user_id)
        )
        conn.commit()
        db_manager.sync_to_cloud()
        return True
    except Exception as e:
        print(f"Delete photo error: {e}")
        return False

# دوال البحث
def save_search(user_id, query):
    """حفظ عملية بحث"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO searches (user_id, search_query) VALUES (?, ?)',
            (user_id, query)
        )
        conn.commit()
        update_stat('total_searches')
        db_manager.sync_to_cloud()
        return True
    except Exception as e:
        print(f"Save search error: {e}")
        return False

def get_search_history(user_id=None, limit=10):
    """الحصول على سجل البحث"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute(
            'SELECT * FROM searches WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
            (user_id, limit)
        )
    else:
        cursor.execute(
            'SELECT * FROM searches ORDER BY created_at DESC LIMIT ?',
            (limit,)
        )
    searches = cursor.fetchall()
    return searches

# دوال الإحصائيات
def update_stat(stat_name):
    """تحديث إحصائية"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO stats (stat_name, stat_value)
            VALUES (?, 1)
            ON CONFLICT(stat_name) DO UPDATE SET
                stat_value = stat_value + 1,
                updated_at = CURRENT_TIMESTAMP
        ''', (stat_name,))
        conn.commit()
    except Exception as e:
        print(f"Update stat error: {e}")

def get_stats():
    """الحصول على الإحصائيات"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stats')
    stats = cursor.fetchall()
    return stats

# ==================== نظام المزامنة التلقائية ====================

def auto_sync_worker():
    """عامل المزامنة التلقائية في الخلفية"""
    while True:
        time.sleep(300)  # مزامنة كل 5 دقائق
        try:
            print("🔄 Auto-syncing to cloud...")
            db_manager.sync_to_cloud()
        except Exception as e:
            print(f"Auto-sync error: {e}")

# بدء المزامنة التلقائية
sync_thread = threading.Thread(target=auto_sync_worker, daemon=True)
sync_thread.start()

# ==================== تهيئة قاعدة البيانات ====================

init_db()

# ==================== مسارات Flask ====================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/photos')
def get_photos():
    """الحصول على صور عشوائية"""
    photos = []
    for i in range(500):
        photo_id = random.randint(1, 500)
        photos.append({
            "id": photo_id,
            "url": f"https://picsum.photos/id/{photo_id}/400/500",
            "author": f"Photographer {photo_id}",
            "title": f"Image {photo_id}"
        })
    return jsonify(photos)

@app.route('/search')
def search_photos():
    """البحث عن صور"""
    query = request.args.get('q', '')
    user_id = request.args.get('user_id')
    
    if not query:
        return jsonify([])
    
    # حفظ البحث إذا كان المستخدم مسجلاً
    if user_id:
        try:
            save_search(int(user_id), query)
        except:
            pass
    
    # توليد نتائج البحث
    photos = []
    for i in range(50):
        photo_id = random.randint(1, 500)
        photos.append({
            "id": photo_id,
            "url": f"https://picsum.photos/id/{photo_id}/400/500",
            "title": f"{query} - Result {i+1}",
            "description": f"Beautiful photo related to {query}"
        })
    return jsonify(photos)

@app.route('/register', methods=['POST'])
def register():
    """تسجيل مستخدم جديد"""
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    
    if not name or not email:
        return jsonify({
            "success": False,
            "message": "الاسم والبريد الإلكتروني مطلوبان"
        })
    
    # التحقق من صحة البريد الإلكتروني
    if '@' not in email or '.' not in email:
        return jsonify({
            "success": False,
            "message": "صيغة البريد الإلكتروني غير صحيحة"
        })
    
    if add_user(name, email, phone):
        user = get_user_by_email(email)
        return jsonify({
            "success": True,
            "message": "تم إنشاء الحساب بنجاح",
            "user": {
                "id": user['id'],
                "name": user['name'],
                "email": user['email']
            }
        })
    else:
        return jsonify({
            "success": False,
            "message": "البريد الإلكتروني مستخدم بالفعل"
        })

@app.route('/login', methods=['POST'])
def login():
    """تسجيل الدخول"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({"success": False, "message": "البريد الإلكتروني مطلوب"})
    
    user = get_user_by_email(email)
    if user:
        return jsonify({
            "success": True,
            "message": "تم تسجيل الدخول بنجاح",
            "user": {
                "id": user['id'],
                "name": user['name'],
                "email": user['email'],
                "phone": user['phone']
            }
        })
    else:
        return jsonify({
            "success": False,
            "message": "المستخدم غير موجود، يرجى التسجيل أولاً"
        })

@app.route('/users')
def users_list():
    """قائمة المستخدمين"""
    users = get_all_users()
    result = []
    for user in users:
        result.append({
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "phone": user['phone'],
            "created_at": user['created_at']
        })
    return jsonify(result)

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    """ملف المستخدم"""
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "message": "المستخدم غير موجود"})
    
    photos = get_saved_photos(user_id)
    searches = get_search_history(user_id)
    
    return jsonify({
        "success": True,
        "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "phone": user['phone'],
            "created_at": user['created_at']
        },
        "saved_photos": [dict(p) for p in photos],
        "search_history": [dict(s) for s in searches]
    })

@app.route('/save-photo', methods=['POST'])
def save_photo_route():
    """حفظ صورة"""
    data = request.get_json()
    user_id = data.get('user_id')
    photo_url = data.get('photo_url')
    photo_id = data.get('photo_id')
    title = data.get('title', '')
    
    if not user_id or not photo_url:
        return jsonify({
            "success": False,
            "message": "بيانات ناقصة"
        })
    
    # التحقق من وجود المستخدم
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({
            "success": False,
            "message": "المستخدم غير موجود"
        })
    
    if save_photo(user_id, photo_url, photo_id, title):
        return jsonify({
            "success": True,
            
            "message": "تم حفظ الصورة بنجاح"})