#!/usr/bin/env python3
"""
ИГС Web Portal - Main Application
"""

import os
import json
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'

# ============================================
# DATABASE CONNECTION
# ============================================

def get_db():
    """Get database connection"""
    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )
    return conn

def init_db():
    """Initialize database with schema"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        cur.execute(schema_sql)
        conn.commit()
        
        # Create default admin user if not exists
        cur.execute("SELECT id FROM users WHERE username = %s", (Config.DEFAULT_ADMIN_LOGIN,))
        if not cur.fetchone():
            password_hash = bcrypt.hashpw(Config.DEFAULT_ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("""
                INSERT INTO users (username, password_hash, role_id, full_name, is_active)
                SELECT %s, %s, r.id, 'Администратор системы', TRUE
                FROM ref_roles r WHERE r.name = 'admin'
            """, (Config.DEFAULT_ADMIN_LOGIN, password_hash))
            conn.commit()
            print(f"Created default admin user: {Config.DEFAULT_ADMIN_LOGIN}")
        
        cur.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

# ============================================
# USER MODEL
# ============================================

class User(UserMixin):
    def __init__(self, id, username, role_name, full_name=None):
        self.id = id
        self.username = username
        self.role = role_name
        self.full_name = full_name
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_viewer(self):
        return self.role == 'viewer'

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT u.id, u.username, u.full_name, r.name as role_name
            FROM users u
            LEFT JOIN ref_roles r ON u.role_id = r.id
            WHERE u.id = %s AND u.is_active = TRUE
        """, (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['role_name'], user_data['full_name'])
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Доступ запрещён. Требуются права администратора.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# UTILITY FUNCTIONS
# ============================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file, object_type, object_id):
    """Save uploaded file and return file info"""
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        
        # Create subdirectory for object type
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], object_type)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        return {
            'filename': filename,
            'original_filename': secure_filename(file.filename),
            'file_path': f"{object_type}/{filename}",
            'file_size': os.path.getsize(file_path),
            'mime_type': file.content_type
        }
    return None

# ============================================
# ROUTES - AUTH
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT u.id, u.username, u.password_hash, u.full_name, r.name as role_name
                FROM users u
                LEFT JOIN ref_roles r ON u.role_id = r.id
                WHERE u.username = %s AND u.is_active = TRUE
            """, (username,))
            user_data = cur.fetchone()
            
            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                user = User(user_data['id'], user_data['username'], user_data['role_name'], user_data['full_name'])
                login_user(user)
                
                # Update last login
                cur.execute("UPDATE users SET last_login = %s WHERE id = %s", (datetime.now(), user_data['id']))
                conn.commit()
                
                cur.close()
                conn.close()
                
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверное имя пользователя или пароль', 'error')
            
            cur.close()
            conn.close()
        except Exception as e:
            flash(f'Ошибка подключения к базе данных: {e}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# ============================================
# ROUTES - MAIN
# ============================================

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/map')
@login_required
def map_view():
    return render_template('map.html')

# ============================================
# API - REFERENCES
# ============================================

@app.route('/api/references/<ref_type>')
@login_required
def get_references(ref_type):
    """Get reference data"""
    table_map = {
        'roles': 'ref_roles',
        'object_kinds': 'ref_object_kinds',
        'well_types': 'ref_well_types',
        'channel_types': 'ref_channel_types',
        'cable_types': 'ref_cable_types',
        'marker_post_types': 'ref_marker_post_types',
        'object_states': 'ref_object_states',
        'owners': 'owners',
        'contracts': 'contracts'
    }
    
    if ref_type not in table_map:
        return jsonify({'error': 'Unknown reference type'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"SELECT * FROM {table_map[ref_type]} ORDER BY id")
        data = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - MAP DATA
# ============================================

@app.route('/api/map/layers')
@login_required
def get_map_layers():
    """Get available map layers"""
    layers = [
        {'id': 'wells', 'name': 'Колодцы', 'type': 'point', 'visible': True},
        {'id': 'marker_posts', 'name': 'Указательные столбики', 'type': 'point', 'visible': True},
        {'id': 'channel_directions', 'name': 'Направления каналов', 'type': 'line', 'visible': True},
        {'id': 'ground_cables', 'name': 'Кабель в грунте', 'type': 'line', 'visible': True},
        {'id': 'aerial_cables', 'name': 'Воздушные кабели', 'type': 'line', 'visible': True},
        {'id': 'duct_cables', 'name': 'Кабель в канализации', 'type': 'line', 'visible': True}
    ]
    return jsonify(layers)

@app.route('/api/map/geojson/<layer>')
@login_required
def get_layer_geojson(layer):
    """Get GeoJSON for a specific layer"""
    coord_system = request.args.get('crs', 'wgs84')
    geom_col = 'geom_wgs84' if coord_system == 'wgs84' else 'geom_msk86'
    
    table_map = {
        'wells': ('wells', 'ref_well_types', 'well_type_id', 'Point'),
        'marker_posts': ('marker_posts', 'ref_marker_post_types', 'marker_type_id', 'Point'),
        'channel_directions': ('channel_directions', None, None, 'LineString'),
        'ground_cables': ('ground_cables', 'ref_cable_types', 'cable_type_id', 'LineString'),
        'aerial_cables': ('aerial_cables', 'ref_cable_types', 'cable_type_id', 'LineString'),
        'duct_cables': ('duct_cables', 'ref_cable_types', 'cable_type_id', 'LineString')
    }
    
    if layer not in table_map:
        return jsonify({'error': 'Unknown layer'}), 400
    
    table, type_table, type_fk, geom_type = table_map[layer]
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        if type_table:
            query = f"""
                SELECT 
                    t.id, t.number, 
                    ST_AsGeoJSON(t.{geom_col})::json as geometry,
                    tt.name as type_name,
                    os.name as state_name,
                    os.color as state_color,
                    o.organization_name as owner_name
                FROM {table} t
                LEFT JOIN {type_table} tt ON t.{type_fk} = tt.id
                LEFT JOIN ref_object_states os ON t.state_id = os.id
                LEFT JOIN owners o ON t.owner_id = o.id
                WHERE t.{geom_col} IS NOT NULL
            """
        else:
            query = f"""
                SELECT 
                    t.id, t.number,
                    ST_AsGeoJSON(t.{geom_col})::json as geometry,
                    NULL as type_name,
                    NULL as state_name,
                    '#3498db' as state_color,
                    o.organization_name as owner_name
                FROM {table} t
                LEFT JOIN owners o ON t.owner_id = o.id
                WHERE t.{geom_col} IS NOT NULL
            """
        
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Build GeoJSON FeatureCollection
        features = []
        for row in rows:
            if row['geometry']:
                feature = {
                    'type': 'Feature',
                    'id': row['id'],
                    'geometry': row['geometry'],
                    'properties': {
                        'id': row['id'],
                        'number': row['number'],
                        'layer': layer,
                        'type_name': row['type_name'],
                        'state_name': row['state_name'],
                        'state_color': row['state_color'],
                        'owner_name': row['owner_name']
                    }
                }
                features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return jsonify(geojson)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - OBJECTS CRUD
# ============================================

@app.route('/api/objects/<object_type>', methods=['GET'])
@login_required
def get_objects(object_type):
    """Get all objects of a type"""
    table_map = {
        'wells': 'wells',
        'marker_posts': 'marker_posts',
        'channel_directions': 'channel_directions',
        'cable_channels': 'cable_channels',
        'ground_cables': 'ground_cables',
        'aerial_cables': 'aerial_cables',
        'duct_cables': 'duct_cables'
    }
    
    if object_type not in table_map:
        return jsonify({'error': 'Unknown object type'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get objects with geometry as GeoJSON
        if object_type == 'cable_channels':
            query = """
                SELECT cc.*, cd.number as direction_number
                FROM cable_channels cc
                LEFT JOIN channel_directions cd ON cc.channel_direction_id = cd.id
                ORDER BY cc.id
            """
        else:
            query = f"""
                SELECT id, number, 
                    ST_AsGeoJSON(geom_wgs84)::json as geom_wgs84,
                    ST_AsGeoJSON(geom_msk86)::json as geom_msk86,
                    owner_id, state_id, description,
                    created_at, updated_at
                FROM {table_map[object_type]}
                ORDER BY id
            """
        
        cur.execute(query)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/objects/<object_type>/<int:object_id>', methods=['GET'])
@login_required
def get_object(object_type, object_id):
    """Get single object by ID"""
    table_map = {
        'wells': 'wells',
        'marker_posts': 'marker_posts',
        'channel_directions': 'channel_directions',
        'cable_channels': 'cable_channels',
        'ground_cables': 'ground_cables',
        'aerial_cables': 'aerial_cables',
        'duct_cables': 'duct_cables'
    }
    
    if object_type not in table_map:
        return jsonify({'error': 'Unknown object type'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if object_type == 'cable_channels':
            query = "SELECT * FROM cable_channels WHERE id = %s"
        else:
            query = f"""
                SELECT *, 
                    ST_AsGeoJSON(geom_wgs84)::json as geom_wgs84,
                    ST_AsGeoJSON(geom_msk86)::json as geom_msk86,
                    ST_X(geom_wgs84) as lon_wgs84,
                    ST_Y(geom_wgs84) as lat_wgs84
                FROM {table_map[object_type]} WHERE id = %s
            """
        
        cur.execute(query, (object_id,))
        data = cur.fetchone()
        
        # Get photos
        if data:
            cur.execute("""
                SELECT id, filename, original_filename, file_path, description
                FROM object_photos
                WHERE object_type = %s AND object_id = %s
                ORDER BY photo_order
            """, (object_type, object_id))
            data['photos'] = cur.fetchall()
        
        cur.close()
        conn.close()
        return jsonify(data) if data else jsonify({'error': 'Not found'}), 404 if not data else 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/objects/<object_type>', methods=['POST'])
@login_required
def create_object(object_type):
    """Create new object"""
    if current_user.is_viewer():
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    table_map = {
        'wells': ('wells', ['number', 'owner_id', 'well_type_id', 'state_id', 'description']),
        'marker_posts': ('marker_posts', ['number', 'owner_id', 'marker_type_id', 'state_id', 'description']),
        'channel_directions': ('channel_directions', ['number', 'owner_id', 'start_well_id', 'end_well_id', 'description']),
        'ground_cables': ('ground_cables', ['number', 'owner_id', 'cable_type_id', 'contract_id', 'state_id', 'description']),
        'aerial_cables': ('aerial_cables', ['number', 'owner_id', 'cable_type_id', 'contract_id', 'state_id', 'description']),
        'duct_cables': ('duct_cables', ['number', 'owner_id', 'cable_type_id', 'contract_id', 'state_id', 'description'])
    }
    
    if object_type not in table_map:
        return jsonify({'error': 'Unknown object type'}), 400
    
    table, fields = table_map[object_type]
    data = request.get_json()
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build insert query
        insert_fields = ['created_by', 'updated_by']
        insert_values = [current_user.id, current_user.id]
        
        for field in fields:
            if field in data:
                insert_fields.append(field)
                insert_values.append(data[field])
        
        # Handle geometry
        if 'lat' in data and 'lon' in data:
            insert_fields.append('geom_wgs84')
            insert_values.append(f"SRID=4326;POINT({data['lon']} {data['lat']})")
        elif 'coordinates' in data:
            # For line geometries
            coords = data['coordinates']
            if len(coords) >= 2:
                coord_str = ', '.join([f"{c[0]} {c[1]}" for c in coords])
                insert_fields.append('geom_wgs84')
                insert_values.append(f"SRID=4326;LINESTRING({coord_str})")
        
        placeholders = ', '.join(['%s'] * len(insert_values))
        field_names = ', '.join(insert_fields)
        
        # Handle geometry placeholder specially
        placeholders_list = []
        for i, f in enumerate(insert_fields):
            if f == 'geom_wgs84':
                placeholders_list.append('ST_GeomFromEWKT(%s)')
            else:
                placeholders_list.append('%s')
        
        query = f"""
            INSERT INTO {table} ({field_names})
            VALUES ({', '.join(placeholders_list)})
            RETURNING id
        """
        
        cur.execute(query, insert_values)
        new_id = cur.fetchone()['id']
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'id': new_id, 'message': 'Объект создан'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/objects/<object_type>/<int:object_id>', methods=['PUT'])
@login_required
def update_object(object_type, object_id):
    """Update existing object"""
    if current_user.is_viewer():
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    table_map = {
        'wells': 'wells',
        'marker_posts': 'marker_posts',
        'channel_directions': 'channel_directions',
        'ground_cables': 'ground_cables',
        'aerial_cables': 'aerial_cables',
        'duct_cables': 'duct_cables'
    }
    
    if object_type not in table_map:
        return jsonify({'error': 'Unknown object type'}), 400
    
    data = request.get_json()
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Build update query dynamically
        updates = ['updated_at = CURRENT_TIMESTAMP', 'updated_by = %s']
        values = [current_user.id]
        
        # Standard fields
        for field in ['number', 'owner_id', 'state_id', 'description', 'well_type_id', 
                      'marker_type_id', 'cable_type_id', 'contract_id', 'start_well_id', 'end_well_id']:
            if field in data:
                updates.append(f"{field} = %s")
                values.append(data[field])
        
        # Handle geometry
        if 'lat' in data and 'lon' in data:
            updates.append("geom_wgs84 = ST_GeomFromEWKT(%s)")
            values.append(f"SRID=4326;POINT({data['lon']} {data['lat']})")
        elif 'coordinates' in data:
            coords = data['coordinates']
            if len(coords) >= 2:
                coord_str = ', '.join([f"{c[0]} {c[1]}" for c in coords])
                updates.append("geom_wgs84 = ST_GeomFromEWKT(%s)")
                values.append(f"SRID=4326;LINESTRING({coord_str})")
        
        values.append(object_id)
        
        query = f"UPDATE {table_map[object_type]} SET {', '.join(updates)} WHERE id = %s"
        cur.execute(query, values)
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Объект обновлён'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/objects/<object_type>/<int:object_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_object(object_type, object_id):
    """Delete object (admin only)"""
    table_map = {
        'wells': 'wells',
        'marker_posts': 'marker_posts',
        'channel_directions': 'channel_directions',
        'cable_channels': 'cable_channels',
        'ground_cables': 'ground_cables',
        'aerial_cables': 'aerial_cables',
        'duct_cables': 'duct_cables'
    }
    
    if object_type not in table_map:
        return jsonify({'error': 'Unknown object type'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Delete photos first
        cur.execute("DELETE FROM object_photos WHERE object_type = %s AND object_id = %s", 
                   (object_type, object_id))
        
        # Delete object
        cur.execute(f"DELETE FROM {table_map[object_type]} WHERE id = %s", (object_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Объект удалён'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - PHOTOS
# ============================================

@app.route('/api/photos/<object_type>/<int:object_id>', methods=['POST'])
@login_required
def upload_photo(object_type, object_id):
    """Upload photo for object"""
    if current_user.is_viewer():
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo provided'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    file_info = save_uploaded_file(file, object_type, object_id)
    if not file_info:
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            INSERT INTO object_photos (object_type, object_id, filename, original_filename, 
                                       file_path, file_size, mime_type, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (object_type, object_id, file_info['filename'], file_info['original_filename'],
              file_info['file_path'], file_info['file_size'], file_info['mime_type'], current_user.id))
        
        photo_id = cur.fetchone()['id']
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'id': photo_id, 'file_path': file_info['file_path']}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============================================
# API - USERS (Admin)
# ============================================

@app.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    """Get all users"""
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT u.id, u.username, u.full_name, u.email, u.is_active, 
                   u.last_login, u.created_at, r.name as role_name
            FROM users u
            LEFT JOIN ref_roles r ON u.role_id = r.id
            ORDER BY u.id
        """)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create new user"""
    data = request.get_json()
    
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = %s", (data['username'],))
        if cur.fetchone():
            return jsonify({'error': 'Username already exists'}), 400
        
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cur.execute("""
            INSERT INTO users (username, password_hash, role_id, full_name, email, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (data['username'], password_hash, data.get('role_id', 1), 
              data.get('full_name'), data.get('email'), data.get('is_active', True)))
        
        new_id = cur.fetchone()['id']
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'id': new_id, 'message': 'Пользователь создан'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """Update user"""
    data = request.get_json()
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        updates = ['updated_at = CURRENT_TIMESTAMP']
        values = []
        
        if 'full_name' in data:
            updates.append('full_name = %s')
            values.append(data['full_name'])
        if 'email' in data:
            updates.append('email = %s')
            values.append(data['email'])
        if 'role_id' in data:
            updates.append('role_id = %s')
            values.append(data['role_id'])
        if 'is_active' in data:
            updates.append('is_active = %s')
            values.append(data['is_active'])
        if 'password' in data and data['password']:
            password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            updates.append('password_hash = %s')
            values.append(password_hash)
        
        values.append(user_id)
        
        cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", values)
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Пользователь обновлён'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# API - OWNERS & CONTRACTS
# ============================================

@app.route('/api/owners', methods=['GET', 'POST'])
@login_required
def owners():
    if request.method == 'GET':
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM owners ORDER BY organization_name")
            data = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        if current_user.is_viewer():
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        data = request.get_json()
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                INSERT INTO owners (organization_name, contact_person, phone, email, address)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (data['organization_name'], data.get('contact_person'), 
                  data.get('phone'), data.get('email'), data.get('address')))
            new_id = cur.fetchone()['id']
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'id': new_id}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/contracts', methods=['GET', 'POST'])
@login_required
def contracts():
    if request.method == 'GET':
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT c.*, o.organization_name as owner_name
                FROM contracts c
                LEFT JOIN owners o ON c.owner_id = o.id
                ORDER BY c.contract_date DESC
            """)
            data = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        if current_user.is_viewer():
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        data = request.get_json()
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                INSERT INTO contracts (contract_number, contract_date, owner_id, description)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (data['contract_number'], data['contract_date'], 
                  data.get('owner_id'), data.get('description')))
            new_id = cur.fetchone()['id']
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'id': new_id}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# ============================================
# API - IMPORT
# ============================================

@app.route('/api/import/csv', methods=['POST'])
@login_required
def import_csv():
    """Import data from CSV file"""
    if current_user.is_viewer():
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    from import_utils import CSVImporter
    import tempfile
    
    file = request.files['file']
    object_type = request.form.get('object_type')
    mapping = json.loads(request.form.get('mapping', '{}'))
    
    try:
        # Save temp file
        temp_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
        file.save(temp_path)
        
        # Import using utility class
        conn = get_db()
        importer = CSVImporter(conn)
        result = importer.import_data(temp_path, object_type, mapping, current_user.id)
        conn.close()
        
        # Clean up temp file
        os.remove(temp_path)
        
        # Log import
        log_import(file.filename, 'csv', result)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/tab', methods=['POST'])
@login_required
def import_tab():
    """Import data from MapInfo TAB files"""
    if current_user.is_viewer():
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    from import_utils import MapInfoImporter
    import tempfile
    
    files = request.files.getlist('files')
    object_type = request.form.get('object_type', 'wells')
    mapping = json.loads(request.form.get('mapping', '{}'))
    
    try:
        # Create temp directory for files
        temp_dir = tempfile.mkdtemp()
        tab_path = None
        
        for file in files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(temp_dir, filename)
            file.save(file_path)
            
            if filename.lower().endswith('.tab'):
                tab_path = file_path
        
        if not tab_path:
            return jsonify({'error': 'TAB file not found in upload'}), 400
        
        # Import using utility class
        conn = get_db()
        importer = MapInfoImporter(conn)
        result = importer.import_from_tab(tab_path, object_type, mapping, current_user.id)
        conn.close()
        
        # Clean up temp files
        import shutil
        shutil.rmtree(temp_dir)
        
        # Log import
        log_import(os.path.basename(tab_path), 'tab', result)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/geojson', methods=['POST'])
@login_required
def import_geojson():
    """Import data from GeoJSON file"""
    if current_user.is_viewer():
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    from import_utils import GeoJSONImporter
    import tempfile
    
    file = request.files['file']
    object_type = request.form.get('object_type')
    mapping = json.loads(request.form.get('mapping', '{}'))
    
    try:
        # Save temp file
        temp_path = os.path.join(tempfile.gettempdir(), secure_filename(file.filename))
        file.save(temp_path)
        
        # Import using utility class
        conn = get_db()
        importer = GeoJSONImporter(conn)
        result = importer.import_from_geojson(temp_path, object_type, mapping, current_user.id)
        conn.close()
        
        # Clean up temp file
        os.remove(temp_path)
        
        # Log import
        log_import(file.filename, 'geojson', result)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def log_import(filename, file_type, result):
    """Log import operation to database"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO import_logs (filename, file_type, status, total_records, 
                                     imported_records, failed_records, error_log, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            filename, 
            file_type,
            'completed' if 'error' not in result else 'failed',
            result.get('imported', 0) + result.get('failed', 0),
            result.get('imported', 0),
            result.get('failed', 0),
            json.dumps(result.get('errors', []), ensure_ascii=False),
            current_user.id
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error logging import: {e}")

# ============================================
# API - STATISTICS
# ============================================

@app.route('/api/stats')
@login_required
def get_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        stats = {}
        
        # Count objects
        tables = ['wells', 'marker_posts', 'channel_directions', 'ground_cables', 'aerial_cables', 'duct_cables']
        for table in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cur.fetchone()['count']
        
        # Count by state
        cur.execute("""
            SELECT os.name, COUNT(w.id) as count
            FROM ref_object_states os
            LEFT JOIN wells w ON w.state_id = os.id
            GROUP BY os.id, os.name
        """)
        stats['wells_by_state'] = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    # Initialize database on startup
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
