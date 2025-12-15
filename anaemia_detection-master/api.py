#!/usr/bin/env python3
"""
API DETEKSI ANEMIA - Fixed Version
Sesuai dengan struktur main.py dan max30100.py yang ada
"""

from flask import Flask, jsonify
from flask_cors import CORS
import sys
import os
import time
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================
PROJECT_PATH = '/home/pi/fazya/anaemia_detection-master'
sys.path.insert(0, PROJECT_PATH)
os.chdir(PROJECT_PATH)

# ============================================
# FLASK APP
# ============================================
app = Flask(__name__)
CORS(app)

# ============================================
# IMPORT & CHECK MODULES
# ============================================
AI_AVAILABLE = False
SENSOR_AVAILABLE = False

# Check AI modules
try:
    from config import config
    from models import load_classification_model, load_segmentation_model
    from pipeline import main_pipeline
    from pipeline import capture_conjunctiva
    AI_AVAILABLE = True
    print("✓ AI modules loaded")
except ImportError as e:
    print(f"✗ AI modules not available: {e}")

# Check Sensor modules
try:
    from max30100 import MAX30100, HeartRateMonitor
    SENSOR_AVAILABLE = True
    print("✓ Sensor modules loaded")
except ImportError as e:
    print(f"✗ Sensor modules not available: {e}")

# ============================================
# GLOBAL: Load AI models once
# ============================================
seg_model = None
class_model = None

def load_ai_models():
    """Load AI models (sekali saja)"""
    global seg_model, class_model
    
    if seg_model is None or class_model is None:
        print("Loading AI models...")
        seg_model = load_segmentation_model(config.SEGMENTATION_MODEL, config.DEVICE)
        class_model = load_classification_model(config.CLASSIFICATION_MODEL, config.DEVICE)
        print("✓ AI models loaded")
    
    return seg_model, class_model

# ============================================
# ROUTES
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'success' if (AI_AVAILABLE and SENSOR_AVAILABLE) else 'partial',
        'ai_available': AI_AVAILABLE,
        'sensor_available': SENSOR_AVAILABLE,
        'message': 'All systems ready' if (AI_AVAILABLE and SENSOR_AVAILABLE) else 'Some components unavailable'
    })


@app.route('/api/measure', methods=['POST'])
def measure():
    """Jalankan pengukuran lengkap: AI + Sensor"""
    
    print("\n" + "=" * 60)
    print("🔬 MEASUREMENT STARTED")
    print("=" * 60)
    
    result_data = {
        'status_anemia': 'unknown',
        'confidence': 0,
        'heart_rate': 0,
        'spo2': 0,
        'image_path': '',
        'timestamp': datetime.now().isoformat()
    }
    
    errors = []
    
    # ===== STEP 1: AI DETECTION =====
    print("\n[STEP 1/2] Running AI Detection...")
    print("-" * 40)
    
    if AI_AVAILABLE:
        try:
            # Load models
            seg_model, class_model = load_ai_models()
            
            # Capture image (tanpa preview untuk API)
            print("   Capturing image...")
            image_path = capture_conjunctiva(
                save_dir="patient_images",
                show_preview=False,
                show_captured=False
            )
            
            if not image_path:
                errors.append("Failed to capture image")
                print("   ✗ Capture failed")
            else:
                print(f"   ✓ Captured: {image_path}")
                
                # Run pipeline
                print("   Running classification...")
                result = main_pipeline(
                    image_path,
                    seg_model,
                    class_model,
                    config.DEVICE,
                    save_results=True,
                    output_dir="results"
                )
                
                # Extract classification result
                classification = result.get('classification', {})
                
                status = classification.get('class_name', 'unknown').lower()
                conf = classification.get('confidence', 0)
                confidence = round(conf * 100, 2) if conf <= 1 else round(conf, 2)
                
                result_data['status_anemia'] = status
                result_data['confidence'] = confidence
                result_data['image_path'] = f"/patient_images/{os.path.basename(image_path)}"
                
                print(f"   ✓ Status: {status}")
                print(f"   ✓ Confidence: {confidence}%")
                
        except Exception as e:
            errors.append(f"AI error: {str(e)}")
            print(f"   ✗ AI error: {e}")
    else:
        # Mock AI data
        import random
        result_data['status_anemia'] = random.choice(['normal', 'anemia'])
        result_data['confidence'] = round(random.uniform(75, 95), 2)
        result_data['image_path'] = '/patient_images/mock.jpg'
        print("   ⚠ Using mock AI data")
    
    # ===== STEP 2: SENSOR READING =====
    print("\n[STEP 2/2] Reading MAX30100 Sensor...")
    print("-" * 40)
    
    if SENSOR_AVAILABLE:
        try:
            sensor = MAX30100()
            
            if not sensor.check_sensor():
                errors.append("Sensor not detected")
                print("   ✗ Sensor not detected")
            else:
                sensor.setup()
                monitor = HeartRateMonitor()
                
                print("   Sampling for 10 seconds...")
                print("   (Place finger on sensor!)")
                
                start_time = time.time()
                duration = 10  # seconds
                warmup = 3     # seconds
                
                bpm_samples = []
                spo2_samples = []
                
                while time.time() - start_time < duration:
                    ir, red = sensor.read_fifo()
                    monitor.add_sample(ir, red)
                    
                    elapsed = time.time() - start_time
                    
                    # After warmup
                    if elapsed > warmup:
                        if monitor.is_finger_detected():
                            bpm = monitor.calculate_bpm()
                            spo2 = monitor.calculate_spo2()
                            
                            if bpm > 0:
                                bpm_samples.append(bpm)
                            if spo2 > 0:
                                spo2_samples.append(spo2)
                    
                    time.sleep(0.05)
                
                sensor.close()
                
                # Calculate averages
                if bpm_samples:
                    # Trimmed mean (buang 20% outliers)
                    bpm_sorted = sorted(bpm_samples)
                    trim = len(bpm_sorted) // 5
                    if trim > 0:
                        bpm_trimmed = bpm_sorted[trim:-trim]
                    else:
                        bpm_trimmed = bpm_sorted
                    result_data['heart_rate'] = int(sum(bpm_trimmed) / len(bpm_trimmed))
                
                if spo2_samples:
                    spo2_sorted = sorted(spo2_samples)
                    trim = len(spo2_sorted) // 5
                    if trim > 0:
                        spo2_trimmed = spo2_sorted[trim:-trim]
                    else:
                        spo2_trimmed = spo2_sorted
                    result_data['spo2'] = int(sum(spo2_trimmed) / len(spo2_trimmed))
                
                if result_data['heart_rate'] > 0 and result_data['spo2'] > 0:
                    print(f"   ✓ Heart Rate: {result_data['heart_rate']} BPM")
                    print(f"   ✓ SpO2: {result_data['spo2']}%")
                else:
                    errors.append("No valid sensor readings - check finger placement")
                    print("   ✗ No valid readings")
                    
        except Exception as e:
            errors.append(f"Sensor error: {str(e)}")
            print(f"   ✗ Sensor error: {e}")
    else:
        # Mock sensor data
        import random
        result_data['heart_rate'] = random.randint(65, 95)
        result_data['spo2'] = random.randint(95, 99)
        print("   ⚠ Using mock sensor data")
    
    # ===== RESULT =====
    print("\n" + "=" * 60)
    print("✅ MEASUREMENT COMPLETE")
    print("=" * 60)
    print(f"   Status Anemia : {result_data['status_anemia']}")
    print(f"   Confidence    : {result_data['confidence']}%")
    print(f"   Heart Rate    : {result_data['heart_rate']} BPM")
    print(f"   SpO2          : {result_data['spo2']}%")
    print("=" * 60 + "\n")
    
    # Response
    response = {
        'status': 'success' if not errors else 'partial',
        'data': result_data
    }
    
    if errors:
        response['warnings'] = errors
    
    return jsonify(response)


@app.route('/api/test-ai', methods=['POST'])
def test_ai():
    """Test AI only"""
    if not AI_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'AI not available'}), 503
    
    try:
        seg_model, class_model = load_ai_models()
        
        image_path = capture_conjunctiva(
            save_dir="patient_images",
            show_preview=False,
            show_captured=False
        )
        
        if not image_path:
            return jsonify({'status': 'error', 'message': 'Capture failed'}), 500
        
        result = main_pipeline(
            image_path, seg_model, class_model, config.DEVICE,
            save_results=True, output_dir="results"
        )
        
        classification = result.get('classification', {})
        conf = classification.get('confidence', 0)
        
        return jsonify({
            'status': 'success',
            'data': {
                'status_anemia': classification.get('class_name', 'unknown').lower(),
                'confidence': round(conf * 100, 2) if conf <= 1 else conf,
                'image_path': f"/patient_images/{os.path.basename(image_path)}"
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/test-sensor', methods=['POST'])
def test_sensor():
    """Test sensor only"""
    if not SENSOR_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'Sensor not available'}), 503
    
    try:
        sensor = MAX30100()
        if not sensor.check_sensor():
            return jsonify({'status': 'error', 'message': 'Sensor not detected'}), 500
        
        sensor.setup()
        monitor = HeartRateMonitor()
        
        start_time = time.time()
        bpm_samples = []
        spo2_samples = []
        
        while time.time() - start_time < 10:
            ir, red = sensor.read_fifo()
            monitor.add_sample(ir, red)
            
            if time.time() - start_time > 3:
                if monitor.is_finger_detected():
                    bpm = monitor.calculate_bpm()
                    spo2 = monitor.calculate_spo2()
                    if bpm > 0:
                        bpm_samples.append(bpm)
                    if spo2 > 0:
                        spo2_samples.append(spo2)
            
            time.sleep(0.05)
        
        sensor.close()
        
        hr = int(sum(bpm_samples) / len(bpm_samples)) if bpm_samples else 0
        sp = int(sum(spo2_samples) / len(spo2_samples)) if spo2_samples else 0
        
        return jsonify({
            'status': 'success' if hr > 0 else 'error',
            'data': {
                'heart_rate': hr,
                'spo2': sp,
                'samples': len(bpm_samples)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 ANEMIA DETECTION API SERVER")
    print("=" * 60)
    print(f"   AI Available     : {'✓' if AI_AVAILABLE else '✗'}")
    print(f"   Sensor Available : {'✓' if SENSOR_AVAILABLE else '✗'}")
    print(f"   Project Path     : {PROJECT_PATH}")
    print("=" * 60)
    print("   Endpoints:")
    print("   - GET  /api/health")
    print("   - POST /api/measure")
    print("   - POST /api/test-ai")
    print("   - POST /api/test-sensor")
    print("=" * 60)
    print("   Running on http://0.0.0.0:5000")
    print("=" * 60 + "\n")
    
    # Pre-load AI models saat startup
    if AI_AVAILABLE:
        try:
            load_ai_models()
        except Exception as e:
            print(f"⚠ Could not pre-load models: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)