#!/usr/bin/env python3
"""
API SERVER untuk Sistem Deteksi Anemia
Menghubungkan Laravel (Website) dengan AI Model + Sensor

Port: 5000
Endpoints:
  - GET  /api/health           → Cek API running atau tidak
  - POST /api/measure          → Mulai pengukuran (AI + Sensor)
  - GET  /api/history          → Ambil riwayat pengukuran
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import json
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# ========================================
# KONFIGURASI PATH
# ========================================

# Path ke folder AI project
PROJECT_PATH = '/home/pi/fazya/anaemia-detection-master'
sys.path.append(PROJECT_PATH)

# Import wrapper functions
from models_wrapper import run_classification, read_sensor_data

# ========================================
# INISIALISASI FLASK APP
# ========================================

app = Flask(__name__)
CORS(app)  # Agar bisa diakses dari Laravel (beda domain/port)

# ========================================
# KONFIGURASI DATABASE MYSQL
# ========================================

DB_CONFIG = {
    'host': 'localhost',           # MySQL server
    'database': 'anemalyze_db',    # Nama database Laravel Anda
    'user': 'jya',                # Username MySQL
    'password': 'jyacantik'    # ← GANTI INI dengan password MySQL Anda!
}

# ========================================
# FUNGSI DATABASE
# ========================================

def get_db_connection():
    """
    Membuat koneksi ke database MySQL
    
    Returns:
        connection: MySQL connection object atau None kalau gagal
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("Database connected")
            return connection
    except Error as e:
        print(f" Error connecting to MySQL: {e}")
        return None


def save_to_database(data):
    """
    Menyimpan hasil pengukuran ke database
    
    Args:
        data (dict): Data pengukuran {
            'status_anemia': 'normal' atau 'anemia',
            'confidence': 95.42,
            'heart_rate': 75,
            'spo2': 98,
            'image_path': '/captures/xxx.png'
        }
    
    Returns:
        int: ID dari record yang baru disimpan, atau False kalau gagal
    """
    connection = get_db_connection()
    
    if connection is None:
        print("Cannot save to database: No connection")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Query SQL untuk insert data
        query = """
            INSERT INTO measurements 
            (status_anemia, confidence, heart_rate, spo2, image_path, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        # Data yang akan disimpan
        values = (
            data['status_anemia'],
            data['confidence'],
            data['heart_rate'],
            data['spo2'],
            data['image_path'],
            datetime.now()
        )
        
        # Execute query
        cursor.execute(query, values)
        connection.commit()
        
        # Ambil ID yang baru saja dibuat
        measurement_id = cursor.lastrowid
        
        print(f"✓ Data saved to database with ID: {measurement_id}")
        
        # Cleanup
        cursor.close()
        connection.close()
        
        return measurement_id
        
    except Error as e:
        print(f"✗ Error saving to database: {e}")
        return False


# ========================================
# ENDPOINT 1: HEALTH CHECK
# ========================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Endpoint untuk cek apakah API running atau tidak
    
    Request:
        GET /api/health
    
    Response:
        {
            "status": "success",
            "message": "API is running",
            "timestamp": "2025-01-22T14:30:00"
        }
    """
    return jsonify({
        'status': 'success',
        'message': 'API is running',
        'timestamp': datetime.now().isoformat()
    }), 200


# ========================================
# ENDPOINT 2: MULAI PENGUKURAN (UTAMA)
# ========================================

@app.route('/api/measure', methods=['POST'])
def perform_measurement():
    """
    Endpoint utama untuk melakukan pengukuran anemia
    
    Proses:
        1. Jalankan AI model (capture gambar → klasifikasi)
        2. Baca data sensor (heart rate & SpO2)
        3. Simpan hasil ke database
        4. Return hasil ke Laravel
    
    Request:
        POST /api/measure
        Body: {} (kosong, tidak perlu parameter)
    
    Response:
        {
            "status": "success",
            "message": "Measurement completed successfully",
            "data": {
                "id": 123,
                "status_anemia": "normal",
                "confidence": 95.42,
                "heart_rate": 75,
                "spo2": 98,
                "timestamp": "2025-01-22T14:30:00"
            }
        }
    """
    try:
        print("\n" + "=" * 60)
        print(" NEW MEASUREMENT REQUEST")
        print("=" * 60)
        
        # ============================================
        # STEP 1: JALANKAN AI MODEL
        # ============================================
        
        print("\n[STEP 1/3] Running AI Classification...")
        print("-" * 60)
        
        # Panggil ai_wrapper.py → run_classification()
        ai_result = run_classification()
        
        # Cek apakah AI berhasil
        if not ai_result:
            print("✗ AI classification failed!")
            return jsonify({
                'status': 'error',
                'message': 'AI classification failed'
            }), 500
        
        # Log hasil AI
        print(f"✓ AI Result:")
        print(f"  - Status: {ai_result.get('status', 'unknown')}")
        print(f"  - Confidence: {ai_result.get('confidence', 0) * 100:.2f}%")
        print(f"  - Image: {ai_result.get('image_path', 'none')}")
        
        # ============================================
        # STEP 2: BACA DATA SENSOR
        # ============================================
        
        print("\n[STEP 2/3] Reading Sensor Data...")
        print("-" * 60)
        
        # Panggil sensor_wrapper.py → read_sensor_data()
        sensor_data = read_sensor_data()
        
        # Cek apakah sensor berhasil
        if not sensor_data.get('success', False):
            print("Sensor reading failed, using default values")
            sensor_data = {
                'heart_rate': 0,
                'spo2': 0
            }
        else:
            print(f"Sensor Result:")
            print(f"  - Heart Rate: {sensor_data['heart_rate']} BPM")
            print(f"  - SpO2: {sensor_data['spo2']}%")
        
        # ============================================
        # STEP 3: GABUNGKAN DATA
        # ============================================
        
        print("\n[STEP 3/3] 💾 Saving to Database...")
        print("-" * 60)
        
        # Gabungkan data AI + Sensor
        measurement_data = {
            'status_anemia': ai_result.get('status', 'unknown'),
            'confidence': ai_result.get('confidence', 0.0),
            'heart_rate': sensor_data.get('heart_rate', 0),
            'spo2': sensor_data.get('spo2', 0),
            'image_path': ai_result.get('image_path', ''),
        }
        
        print(f"Data to save:")
        print(f"  - Anemia Status: {measurement_data['status_anemia']}")
        print(f"  - Confidence: {measurement_data['confidence'] * 100:.2f}%")
        print(f"  - Heart Rate: {measurement_data['heart_rate']} BPM")
        print(f"  - SpO2: {measurement_data['spo2']}%")
        print(f"  - Image Path: {measurement_data['image_path']}")
        
        # ============================================
        # STEP 4: SIMPAN KE DATABASE
        # ============================================
        
        measurement_id = save_to_database(measurement_data)
        
        if not measurement_id:
            print(" Failed to save to database!")
            return jsonify({
                'status': 'error',
                'message': 'Failed to save to database'
            }), 500
        
        print(f"✓ Saved successfully with ID: {measurement_id}")
        
        # ============================================
        # STEP 5: RETURN HASIL KE LARAVEL
        # ============================================
        
        print("\n" + "=" * 60)
        print(" MEASUREMENT COMPLETED SUCCESSFULLY!")
        print("=" * 60 + "\n")
        
        return jsonify({
            'status': 'success',
            'message': 'Measurement completed successfully',
            'data': {
                'id': measurement_id,
                'status_anemia': measurement_data['status_anemia'],
                'confidence': round(measurement_data['confidence'] * 100, 2),  # Convert ke persen
                'heart_rate': measurement_data['heart_rate'],
                'spo2': measurement_data['spo2'],
                'image_path': measurement_data['image_path'],
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        # Kalau ada error, print detail error
        print(f"\n✗ ERROR in measurement:")
        print(f"  {str(e)}")
        
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'message': f'Measurement failed: {str(e)}'
        }), 500


# ========================================
# ENDPOINT 3: RIWAYAT PENGUKURAN
# ========================================

@app.route('/api/history', methods=['GET'])
def get_history():
    """
    Endpoint untuk mengambil riwayat pengukuran
    
    Request:
        GET /api/history?limit=10
        
        Query Parameters:
            - limit (optional): Jumlah data yang diambil (default: 10)
    
    Response:
        {
            "status": "success",
            "data": [
                {
                    "id": 123,
                    "status_anemia": "normal",
                    "confidence": 95.42,
                    "heart_rate": 75,
                    "spo2": 98,
                    "created_at": "2025-01-22 14:30:00"
                },
                ...
            ]
        }
    """
    try:
        connection = get_db_connection()
        
        if connection is None:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Ambil parameter limit dari query string
        limit = request.args.get('limit', 10, type=int)
        
        # Query untuk ambil data
        query = """
            SELECT * FROM measurements 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        print(f"✓ Retrieved {len(results)} records from database")
        
        return jsonify({
            'status': 'success',
            'data': results
        }), 200
        
    except Exception as e:
        print(f"✗ Error getting history: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ========================================
# JALANKAN API SERVER
# ========================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 ANEMIA DETECTION API SERVER")
    print("=" * 60)
    print(f"📍 Starting server on http://0.0.0.0:5000")
    print(f"📁 AI Project Path: {PROJECT_PATH}")
    print(f"💾 Database: {DB_CONFIG['database']}")
    print("=" * 60)
    print("\nEndpoints available:")
    print("  GET  /api/health   → Health check")
    print("  POST /api/measure  → Start measurement")
    print("  GET  /api/history  → Get measurement history")
    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")
    
    # Jalankan Flask server
    # host='0.0.0.0' → Bisa diakses dari luar Raspberry Pi
    # port=5000 → Port yang digunakan
    # debug=True → Mode development (auto-reload kalau ada perubahan code)
    app.run(host='0.0.0.0', port=5000, debug=True)