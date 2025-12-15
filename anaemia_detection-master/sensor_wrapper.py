#!/usr/bin/env python3
"""
Wrapper untuk sensor MAX30100
Mengintegrasikan code sensor yang sudah ada dengan API
"""

import sys
import time
import os

# Import class MAX30100 yang sudah ada
# Sesuaikan path dengan lokasi file sensor MAX30100 Anda
SENSOR_FILE_PATH = '/home/pi/fazya/anaemia_detection-master/max30100.py'  # Sesuaikan path file sensor Anda

# Temporary workaround untuk import
import importlib.util
spec = importlib.util.spec_from_file_location("max30100", SENSOR_FILE_PATH)
max30100_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(max30100_module)

MAX30100 = max30100_module.MAX30100
HeartRateMonitor = max30100_module.HeartRateMonitor


def read_sensor_data(duration=10):
    """
    Membaca data dari sensor MAX30100
    
    Args:
        duration: Durasi pembacaan dalam detik (default 10)
        
    Returns:
        dict: {
            'heart_rate': int (BPM),
            'spo2': int (%),
            'success': bool
        }
    """
    print("Starting sensor reading...")
    
    try:
        # Initialize sensor
        sensor = MAX30100()
        
        # Check sensor
        if not sensor.check_sensor():
            print("ERROR: MAX30100 sensor not found!")
            return {
                'heart_rate': 0,
                'spo2': 0,
                'success': False,
                'error': 'Sensor not found'
            }
        
        # Setup sensor
        sensor.setup()
        monitor = HeartRateMonitor()
        
        print(f"Reading sensor for {duration} seconds...")
        print("Place your finger on the sensor...")
        
        start_time = time.time()
        finger_detected_time = 0
        stable_readings = []
        
        while time.time() - start_time < duration:
            # Read data
            ir, red = sensor.read_fifo()
            monitor.add_sample(ir, red)
            
            # Check if finger is detected
            if monitor.is_finger_detected():
                finger_detected_time += 1
                
                # Calculate values
                bpm = monitor.calculate_bpm()
                spo2 = monitor.calculate_spo2()
                
                # Only save if we have valid readings
                if bpm > 0 and spo2 > 0:
                    stable_readings.append({
                        'bpm': bpm,
                        'spo2': spo2
                    })
                    print(f"BPM: {bpm:3d} | SpO2: {spo2:3d}% | Readings: {len(stable_readings)}")
            else:
                print("No finger detected...")
            
            time.sleep(0.05)
        
        # Close sensor
        sensor.close()
        
        # Calculate average from stable readings
        if len(stable_readings) >= 5:
            # Get last 10 readings for better accuracy
            recent_readings = stable_readings[-10:]
            
            avg_bpm = int(sum(r['bpm'] for r in recent_readings) / len(recent_readings))
            avg_spo2 = int(sum(r['spo2'] for r in recent_readings) / len(recent_readings))
            
            print(f"\nFinal readings - BPM: {avg_bpm}, SpO2: {avg_spo2}%")
            
            return {
                'heart_rate': avg_bpm,
                'spo2': avg_spo2,
                'success': True
            }
        else:
            print("\nNot enough stable readings. Please ensure finger is on sensor.")
            return {
                'heart_rate': 0,
                'spo2': 0,
                'success': False,
                'error': 'Not enough stable readings'
            }
            
    except Exception as e:
        print(f"Error reading sensor: {str(e)}")
        return {
            'heart_rate': 0,
            'spo2': 0,
            'success': False,
            'error': str(e)
        }


def quick_read():
    """
    Pembacaan cepat untuk testing (5 detik)
    """
    return read_sensor_data(duration=5)


# Test langsung
if __name__ == '__main__':
    print("Testing MAX30100 Sensor Wrapper")
    print("=" * 50)
    
    result = read_sensor_data(duration=10)
    
    print("\n" + "=" * 50)
    print("Result:")
    print(f"Heart Rate: {result['heart_rate']} BPM")
    print(f"SpO2: {result['spo2']}%")
    print(f"Success: {result['success']}")
    if 'error' in result:
        print(f"Error: {result['error']}")