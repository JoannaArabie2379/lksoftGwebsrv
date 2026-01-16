"""
ИГС Portal - Data Import Utilities
Supports CSV and MapInfo TAB/DAT/MAP/ID files
"""

import os
import csv
import struct
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from shapely import wkt
from shapely.geometry import Point, LineString, Polygon, mapping


class CSVImporter:
    """Import data from CSV files"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def preview(self, file_path: str, encoding: str = 'utf-8') -> Dict:
        """Preview CSV file structure"""
        try:
            df = pd.read_csv(file_path, nrows=5, encoding=encoding)
            return {
                'columns': list(df.columns),
                'sample': df.to_dict('records'),
                'total_rows': sum(1 for _ in open(file_path, encoding=encoding)) - 1
            }
        except Exception as e:
            return {'error': str(e)}
    
    def import_data(self, file_path: str, object_type: str, mapping: Dict[str, str], 
                    user_id: int, encoding: str = 'utf-8') -> Dict:
        """
        Import CSV data into database
        
        Args:
            file_path: Path to CSV file
            object_type: Target table (wells, marker_posts, etc.)
            mapping: Dict mapping CSV columns to DB columns
            user_id: ID of user performing import
            encoding: File encoding
            
        Returns:
            Dict with import results
        """
        results = {
            'imported': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            cur = self.conn.cursor()
            
            # Table configuration
            table_config = {
                'wells': {
                    'table': 'wells',
                    'geom_type': 'POINT',
                    'required': ['number']
                },
                'marker_posts': {
                    'table': 'marker_posts',
                    'geom_type': 'POINT',
                    'required': ['number']
                },
                'channel_directions': {
                    'table': 'channel_directions',
                    'geom_type': 'LINESTRING',
                    'required': ['number']
                },
                'ground_cables': {
                    'table': 'ground_cables',
                    'geom_type': 'LINESTRING',
                    'required': ['number']
                },
                'aerial_cables': {
                    'table': 'aerial_cables',
                    'geom_type': 'LINESTRING',
                    'required': ['number']
                },
                'duct_cables': {
                    'table': 'duct_cables',
                    'geom_type': 'LINESTRING',
                    'required': ['number']
                }
            }
            
            config = table_config.get(object_type)
            if not config:
                return {'error': f'Unknown object type: {object_type}'}
            
            for idx, row in df.iterrows():
                try:
                    # Build data from mapping
                    data = {}
                    lat = None
                    lon = None
                    
                    for csv_col, db_col in mapping.items():
                        if csv_col in row and pd.notna(row[csv_col]):
                            value = row[csv_col]
                            if db_col == 'lat':
                                lat = float(value)
                            elif db_col == 'lon':
                                lon = float(value)
                            else:
                                data[db_col] = value
                    
                    # Check required fields
                    missing = [f for f in config['required'] if f not in data]
                    if missing:
                        results['errors'].append(f"Row {idx+1}: Missing required fields: {missing}")
                        results['failed'] += 1
                        continue
                    
                    # Build insert query
                    fields = ['created_by', 'updated_by']
                    values = [user_id, user_id]
                    placeholders = ['%s', '%s']
                    
                    for field, value in data.items():
                        fields.append(field)
                        values.append(value)
                        placeholders.append('%s')
                    
                    # Add geometry
                    if lat is not None and lon is not None:
                        fields.append('geom_wgs84')
                        values.append(f'SRID=4326;POINT({lon} {lat})')
                        placeholders.append('ST_GeomFromEWKT(%s)')
                    
                    query = f"""
                        INSERT INTO {config['table']} ({', '.join(fields)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    cur.execute(query, values)
                    results['imported'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Row {idx+1}: {str(e)}")
                    results['failed'] += 1
            
            self.conn.commit()
            cur.close()
            
        except Exception as e:
            results['error'] = str(e)
        
        return results


class MapInfoImporter:
    """Import data from MapInfo TAB files"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def read_tab_file(self, tab_path: str) -> Dict:
        """
        Read MapInfo TAB file structure
        
        TAB file is a text file containing metadata about the layer
        """
        metadata = {
            'columns': [],
            'charset': 'WindowsCyrillic',
            'bounds': None,
            'dat_file': None,
            'map_file': None,
            'id_file': None
        }
        
        try:
            with open(tab_path, 'r', encoding='cp1251') as f:
                content = f.read()
            
            lines = content.split('\n')
            in_fields = False
            
            for line in lines:
                line = line.strip()
                
                if line.lower().startswith('!table'):
                    continue
                elif line.lower().startswith('!version'):
                    continue
                elif line.lower().startswith('charset'):
                    metadata['charset'] = line.split('"')[1] if '"' in line else 'WindowsCyrillic'
                elif line.lower().startswith('definition table'):
                    continue
                elif line.lower().startswith('file'):
                    # Get associated DAT file
                    parts = line.split('"')
                    if len(parts) >= 2:
                        metadata['dat_file'] = parts[1]
                elif line.lower().startswith('fields'):
                    in_fields = True
                    # Extract field count
                    count = int(line.split()[1]) if len(line.split()) > 1 else 0
                elif in_fields and line:
                    # Parse field definition
                    # Format: FieldName Type [(Width, Precision)]
                    parts = line.split()
                    if parts:
                        field_name = parts[0]
                        field_type = parts[1] if len(parts) > 1 else 'Char'
                        metadata['columns'].append({
                            'name': field_name,
                            'type': field_type
                        })
                        
        except Exception as e:
            metadata['error'] = str(e)
        
        return metadata
    
    def read_dat_file(self, dat_path: str, columns: List[Dict], encoding: str = 'cp1251') -> List[Dict]:
        """
        Read MapInfo DAT file (dBASE format)
        """
        records = []
        
        try:
            with open(dat_path, 'rb') as f:
                # Read dBASE header
                version = struct.unpack('B', f.read(1))[0]
                year, month, day = struct.unpack('3B', f.read(3))
                num_records = struct.unpack('<I', f.read(4))[0]
                header_size = struct.unpack('<H', f.read(2))[0]
                record_size = struct.unpack('<H', f.read(2))[0]
                
                f.seek(32)  # Skip to field descriptors
                
                # Read field descriptors
                fields = []
                while True:
                    byte = f.read(1)
                    if byte == b'\r' or byte == b'':
                        break
                    f.seek(-1, 1)
                    
                    field_name = f.read(11).decode('ascii', errors='ignore').strip('\x00')
                    field_type = f.read(1).decode('ascii')
                    f.read(4)  # Reserved
                    field_length = struct.unpack('B', f.read(1))[0]
                    decimal_count = struct.unpack('B', f.read(1))[0]
                    f.read(14)  # Reserved
                    
                    fields.append({
                        'name': field_name,
                        'type': field_type,
                        'length': field_length,
                        'decimal': decimal_count
                    })
                
                # Read records
                f.seek(header_size)
                
                for i in range(num_records):
                    record = {}
                    deleted = f.read(1)
                    
                    if deleted == b'*':
                        # Skip deleted record
                        f.read(record_size - 1)
                        continue
                    
                    for field in fields:
                        value = f.read(field['length']).decode(encoding, errors='ignore').strip()
                        
                        # Convert value based on type
                        if field['type'] == 'N':
                            try:
                                if field['decimal'] > 0:
                                    value = float(value) if value else None
                                else:
                                    value = int(value) if value else None
                            except:
                                value = None
                        elif field['type'] == 'D':
                            try:
                                value = datetime.strptime(value, '%Y%m%d').date() if value else None
                            except:
                                value = None
                        elif field['type'] == 'L':
                            value = value.upper() in ('T', 'Y', '1')
                        
                        record[field['name']] = value
                    
                    records.append(record)
                    
        except Exception as e:
            print(f"Error reading DAT file: {e}")
        
        return records
    
    def read_map_file(self, map_path: str) -> List[Dict]:
        """
        Read MapInfo MAP file (binary geometry file)
        This is a simplified parser - MapInfo MAP format is complex
        """
        geometries = []
        
        try:
            with open(map_path, 'rb') as f:
                # MAP file header
                header = f.read(100)
                
                # The full MAP format parsing is very complex
                # For production use, consider using GDAL/OGR
                # This is a placeholder that returns empty geometries
                
        except Exception as e:
            print(f"Error reading MAP file: {e}")
        
        return geometries
    
    def import_from_tab(self, tab_path: str, object_type: str, mapping: Dict[str, str],
                        user_id: int, source_srid: int = 4326) -> Dict:
        """
        Import MapInfo TAB file set into database
        
        Args:
            tab_path: Path to .TAB file
            object_type: Target table type
            mapping: Column mapping
            user_id: Importing user ID
            source_srid: Source coordinate system SRID
        """
        results = {
            'imported': 0,
            'failed': 0,
            'errors': [],
            'warnings': []
        }
        
        # Get base path
        base_path = os.path.splitext(tab_path)[0]
        dat_path = base_path + '.DAT'
        map_path = base_path + '.MAP'
        id_path = base_path + '.ID'
        
        # Check required files
        if not os.path.exists(dat_path):
            dat_path = base_path + '.dat'
        if not os.path.exists(map_path):
            map_path = base_path + '.map'
        
        if not os.path.exists(dat_path):
            results['error'] = f'DAT file not found: {dat_path}'
            return results
        
        # Read TAB metadata
        metadata = self.read_tab_file(tab_path)
        if 'error' in metadata:
            results['warnings'].append(f"TAB parsing warning: {metadata['error']}")
        
        # Read attribute data
        records = self.read_dat_file(dat_path, metadata.get('columns', []))
        
        results['warnings'].append(
            "Note: Geometry import from MAP files requires GDAL/OGR. "
            "Only attribute data was imported. Use QGIS or other GIS software "
            "to export to a format with embedded geometry (GeoJSON, CSV with WKT)."
        )
        
        # Import records (without geometry for now)
        try:
            cur = self.conn.cursor()
            
            table_map = {
                'wells': 'wells',
                'marker_posts': 'marker_posts',
                'channel_directions': 'channel_directions',
                'ground_cables': 'ground_cables',
                'aerial_cables': 'aerial_cables',
                'duct_cables': 'duct_cables'
            }
            
            table = table_map.get(object_type)
            if not table:
                results['error'] = f'Unknown object type: {object_type}'
                return results
            
            for idx, record in enumerate(records):
                try:
                    data = {}
                    for src_col, dst_col in mapping.items():
                        if src_col in record and record[src_col] is not None:
                            data[dst_col] = record[src_col]
                    
                    if 'number' not in data:
                        data['number'] = f'IMP-{idx+1}'
                    
                    fields = ['created_by', 'updated_by']
                    values = [user_id, user_id]
                    
                    for field, value in data.items():
                        fields.append(field)
                        values.append(value)
                    
                    placeholders = ['%s'] * len(values)
                    
                    query = f"""
                        INSERT INTO {table} ({', '.join(fields)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    cur.execute(query, values)
                    results['imported'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Record {idx+1}: {str(e)}")
                    results['failed'] += 1
            
            self.conn.commit()
            cur.close()
            
        except Exception as e:
            results['error'] = str(e)
        
        return results


class GeoJSONImporter:
    """Import data from GeoJSON files"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def import_from_geojson(self, file_path: str, object_type: str, 
                            mapping: Dict[str, str], user_id: int) -> Dict:
        """Import GeoJSON file into database"""
        results = {
            'imported': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                geojson = json.load(f)
            
            features = geojson.get('features', [])
            cur = self.conn.cursor()
            
            table_map = {
                'wells': ('wells', 'POINT'),
                'marker_posts': ('marker_posts', 'POINT'),
                'channel_directions': ('channel_directions', 'LINESTRING'),
                'ground_cables': ('ground_cables', 'LINESTRING'),
                'aerial_cables': ('aerial_cables', 'LINESTRING'),
                'duct_cables': ('duct_cables', 'LINESTRING')
            }
            
            table, expected_type = table_map.get(object_type, (None, None))
            if not table:
                results['error'] = f'Unknown object type: {object_type}'
                return results
            
            for idx, feature in enumerate(features):
                try:
                    props = feature.get('properties', {})
                    geom = feature.get('geometry')
                    
                    # Map properties
                    data = {}
                    for src_col, dst_col in mapping.items():
                        if src_col in props and props[src_col] is not None:
                            data[dst_col] = props[src_col]
                    
                    if 'number' not in data:
                        data['number'] = f'GEO-{idx+1}'
                    
                    fields = ['created_by', 'updated_by']
                    values = [user_id, user_id]
                    placeholders = ['%s', '%s']
                    
                    for field, value in data.items():
                        fields.append(field)
                        values.append(value)
                        placeholders.append('%s')
                    
                    # Add geometry
                    if geom:
                        geom_json = json.dumps(geom)
                        fields.append('geom_wgs84')
                        values.append(geom_json)
                        placeholders.append('ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)')
                    
                    query = f"""
                        INSERT INTO {table} ({', '.join(fields)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    cur.execute(query, values)
                    results['imported'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Feature {idx+1}: {str(e)}")
                    results['failed'] += 1
            
            self.conn.commit()
            cur.close()
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
