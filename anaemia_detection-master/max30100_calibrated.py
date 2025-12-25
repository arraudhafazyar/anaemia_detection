#!/usr/bin/env python3
"""
MAX30100 Calibration Script
Gunakan script ini untuk mengkalibrasi sensor dengan pulse oximeter standar
"""

from smbus2 import SMBus
import time
import numpy as np
from collections import deque

# MAX30100 I2C Address & Registers
MAX30100_ADDRESS = 0x57
REG_FIFO_DATA = 0x05
REG_MODE_CONFIG = 0x06
REG_SPO2_CONFIG = 0x07
REG_LED_CONFIG = 0x09

MODE_RESET = 0x40
MODE_SPO2_EN = 0x03
SPO2_HI_RES_EN = 0x40
SAMPLE_RATE_100HZ = 0x00
LED_PW_1600US_16BITS = 0x03


class MAX30100Calibration:
    def __init__(self):
        self.bus = SMBus(1)
        self.address = MAX30100_ADDRESS
        self.ir_buffer = deque(maxlen=100)
        self.red_buffer = deque(maxlen=100)
        
    def write_register(self, register, value):
        self.bus.write_byte_data(self.address, register, value)
        time.sleep(0.01)
        
    def read_register(self, register):
        return self.bus.read_byte_data(self.address, register)
    
    def setup(self):
        """Setup sensor"""
        # Reset
        self.write_register(REG_MODE_CONFIG, MODE_RESET)
        time.sleep(0.1)
        
        # SpO2 config
        spo2_config = SPO2_HI_RES_EN | SAMPLE_RATE_100HZ | LED_PW_1600US_16BITS
        self.write_register(REG_SPO2_CONFIG, spo2_config)
        
        # LED config - coba berbagai intensitas
        # Format: (IR << 4) | RED
        # Range: 0x00 - 0x0F (0-50mA)
        led_config = (0x0F << 4) | 0x0F  # Maximum brightness
        self.write_register(REG_LED_CONFIG, led_config)
        
        # Enable SpO2 mode
        self.write_register(REG_MODE_CONFIG, MODE_SPO2_EN)
        print("Sensor configured!")
        
    def read_fifo(self):
        data = self.bus.read_i2c_block_data(self.address, REG_FIFO_DATA, 4)
        ir = (data[0] << 8) | data[1]
        red = (data[2] << 8) | data[3]
        return ir, red
    
    def collect_samples(self, duration=10):
        """Collect samples for specified duration"""
        print(f"\nCollecting data for {duration} seconds...")
        print("Keep your finger steady on the sensor!")
        
        start_time = time.time()
        samples_ir = []
        samples_red = []
        
        while time.time() - start_time < duration:
            ir, red = self.read_fifo()
            
            # Only add if finger detected
            if ir > 10000 and red > 5000:
                samples_ir.append(ir)
                samples_red.append(red)
                
            elapsed = time.time() - start_time
            print(f"\r  Time: {elapsed:.1f}s | IR: {ir:5d} | Red: {red:5d} | Samples: {len(samples_ir)}", end="")
            time.sleep(0.05)
        
        print()
        return np.array(samples_ir), np.array(samples_red)
    
    def calculate_r_ratio(self, ir_data, red_data):
        """Calculate R ratio for SpO2"""
        if len(ir_data) < 30:
            return None
            
        # AC component (variasi) - gunakan standar deviasi
        ir_ac = np.std(ir_data)
        red_ac = np.std(red_data)
        
        # DC component (rata-rata)
        ir_dc = np.mean(ir_data)
        red_dc = np.mean(red_data)
        
        if ir_dc == 0 or red_dc == 0 or ir_ac == 0:
            return None
            
        # R ratio
        r = (red_ac / red_dc) / (ir_ac / ir_dc)
        
        return r, ir_ac, ir_dc, red_ac, red_dc
    
    def close(self):
        self.bus.close()


def main():
    print("=" * 60)
    print("   MAX30100 CALIBRATION TOOL")
    print("=" * 60)
    print()
    print("Siapkan pulse oximeter standar untuk pembanding!")
    print()
    
    sensor = MAX30100Calibration()
    sensor.setup()
    
    calibration_data = []
    
    while True:
        print("\n" + "-" * 60)
        print("MENU:")
        print("  1. Ambil data kalibrasi (bandingkan dengan oximeter standar)")
        print("  2. Lihat hasil kalibrasi")
        print("  3. Hitung formula baru")
        print("  4. Test formula baru")
        print("  5. Keluar")
        print("-" * 60)
        
        choice = input("Pilihan: ").strip()
        
        if choice == "1":
            # Ambil data kalibrasi
            actual_spo2 = input("\nMasukkan SpO2 dari pulse oximeter standar (%): ").strip()
            actual_bpm = input("Masukkan BPM dari pulse oximeter standar: ").strip()
            
            try:
                actual_spo2 = float(actual_spo2)
                actual_bpm = float(actual_bpm)
            except:
                print("Input tidak valid!")
                continue
            
            print("\nLetakkan jari di sensor MAX30100...")
            time.sleep(2)
            
            # Collect samples
            ir_data, red_data = sensor.collect_samples(duration=10)
            
            if len(ir_data) < 50:
                print("❌ Data tidak cukup! Pastikan jari menempel dengan baik.")
                continue
            
            # Calculate R ratio
            result = sensor.calculate_r_ratio(ir_data, red_data)
            
            if result is None:
                print("❌ Gagal menghitung R ratio!")
                continue
                
            r, ir_ac, ir_dc, red_ac, red_dc = result
            
            print(f"\n✓ Data berhasil diambil!")
            print(f"  IR  - AC: {ir_ac:.2f}, DC: {ir_dc:.2f}")
            print(f"  Red - AC: {red_ac:.2f}, DC: {red_dc:.2f}")
            print(f"  R Ratio: {r:.4f}")
            print(f"  SpO2 Standar: {actual_spo2}%")
            
            calibration_data.append({
                'actual_spo2': actual_spo2,
                'actual_bpm': actual_bpm,
                'r_ratio': r,
                'ir_ac': ir_ac,
                'ir_dc': ir_dc,
                'red_ac': red_ac,
                'red_dc': red_dc
            })
            
            print(f"\n  Total data kalibrasi: {len(calibration_data)}")
            
        elif choice == "2":
            # Lihat hasil
            if not calibration_data:
                print("\n❌ Belum ada data kalibrasi!")
                continue
                
            print("\n" + "=" * 60)
            print("DATA KALIBRASI")
            print("=" * 60)
            print(f"{'No':<4} {'SpO2 Std':<10} {'R Ratio':<10} {'SpO2 Old':<10}")
            print("-" * 60)
            
            for i, data in enumerate(calibration_data):
                # Formula lama
                old_spo2 = 110.0 - 25.0 * data['r_ratio']
                
                print(f"{i+1:<4} {data['actual_spo2']:<10.1f} {data['r_ratio']:<10.4f} {old_spo2:<10.1f}")
            
            print("-" * 60)
            
        elif choice == "3":
            # Hitung formula baru dengan linear regression
            if len(calibration_data) < 3:
                print("\n❌ Minimal 3 data untuk kalibrasi! (Saat ini: {})".format(len(calibration_data)))
                print("   Ambil data di berbagai kondisi:")
                print("   - SpO2 tinggi (98-100%)")
                print("   - SpO2 sedang (95-97%)")
                print("   - SpO2 rendah (jika memungkinkan)")
                continue
            
            # Extract data
            r_values = np.array([d['r_ratio'] for d in calibration_data])
            spo2_values = np.array([d['actual_spo2'] for d in calibration_data])
            
            # Linear regression: SpO2 = a - b * R
            # Menggunakan least squares
            A = np.vstack([np.ones(len(r_values)), r_values]).T
            coeffs = np.linalg.lstsq(A, spo2_values, rcond=None)[0]
            
            a = coeffs[0]  # Intercept
            b = -coeffs[1]  # Slope (negative karena SpO2 turun saat R naik)
            
            print("\n" + "=" * 60)
            print("HASIL KALIBRASI")
            print("=" * 60)
            print(f"\nFormula LAMA: SpO2 = 110.0 - 25.0 * R")
            print(f"Formula BARU: SpO2 = {a:.2f} - {b:.2f} * R")
            print()
            
            # Show comparison
            print(f"{'R Ratio':<10} {'SpO2 Std':<10} {'SpO2 Old':<10} {'SpO2 New':<10} {'Error Old':<10} {'Error New':<10}")
            print("-" * 70)
            
            total_error_old = 0
            total_error_new = 0
            
            for data in calibration_data:
                r = data['r_ratio']
                actual = data['actual_spo2']
                old = 110.0 - 25.0 * r
                new = a - b * r
                
                err_old = abs(actual - old)
                err_new = abs(actual - new)
                
                total_error_old += err_old
                total_error_new += err_new
                
                print(f"{r:<10.4f} {actual:<10.1f} {old:<10.1f} {new:<10.1f} {err_old:<10.2f} {err_new:<10.2f}")
            
            print("-" * 70)
            avg_err_old = total_error_old / len(calibration_data)
            avg_err_new = total_error_new / len(calibration_data)
            print(f"{'AVG ERROR:':<42} {avg_err_old:<10.2f} {avg_err_new:<10.2f}")
            
            print(f"\n✓ Formula baru mengurangi error dari {avg_err_old:.2f}% menjadi {avg_err_new:.2f}%")
            print(f"\n📝 Update di max30100.py:")
            print(f"   spo2 = {a:.2f} - {b:.2f} * r")
            
        elif choice == "4":
            # Test formula real-time
            print("\nMasukkan koefisien formula baru (SpO2 = a - b * R):")
            try:
                a = float(input("  a (intercept): ").strip())
                b = float(input("  b (slope): ").strip())
            except:
                print("Input tidak valid!")
                continue
            
            print(f"\nFormula: SpO2 = {a:.2f} - {b:.2f} * R")
            print("Letakkan jari di sensor... (Ctrl+C untuk stop)")
            
            ir_buf = deque(maxlen=100)
            red_buf = deque(maxlen=100)
            
            try:
                while True:
                    ir, red = sensor.read_fifo()
                    
                    if ir > 10000 and red > 5000:
                        ir_buf.append(ir)
                        red_buf.append(red)
                        
                        if len(ir_buf) >= 30:
                            ir_ac = np.std(list(ir_buf))
                            ir_dc = np.mean(list(ir_buf))
                            red_ac = np.std(list(red_buf))
                            red_dc = np.mean(list(red_buf))
                            
                            if ir_dc > 0 and red_dc > 0 and ir_ac > 0:
                                r = (red_ac / red_dc) / (ir_ac / ir_dc)
                                
                                spo2_old = 110.0 - 25.0 * r
                                spo2_new = a - b * r
                                
                                # Clamp values
                                spo2_old = max(70, min(100, spo2_old))
                                spo2_new = max(70, min(100, spo2_new))
                                
                                print(f"\r  R: {r:.4f} | SpO2 Old: {spo2_old:.1f}% | SpO2 New: {spo2_new:.1f}%   ", end="")
                    else:
                        print(f"\r  IR: {ir:5d} | Red: {red:5d} | Letakkan jari...                    ", end="")
                    
                    time.sleep(0.05)
                    
            except KeyboardInterrupt:
                print("\n\nTest selesai!")
            
        elif choice == "5":
            break
        else:
            print("Pilihan tidak valid!")
    
    sensor.close()
    print("\nSensor closed. Bye!")


if __name__ == "__main__":
    main()