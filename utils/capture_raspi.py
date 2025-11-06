"""
Function: capture_conjunctiva()
Deskripsi:
Menangkap gambar konjungtiva pasien secara manual
dengan menekan ENTER menggunakan Raspberry Pi Camera v3 (Picamera2).
"""

from picamera2 import Picamera2, Preview
from time import sleep
from pathlib import Path
import os

def capture_conjunctiva(save_dir="captures", preview=True):
    """
    Capture gambar konjungtiva secara manual (ENTER trigger)
    dan simpan ke folder 'captures'.
    
    Args:
        save_dir (str): Folder tempat menyimpan hasil foto.
        preview (bool): Tampilkan live preview jika True.
    
    Returns:
        str: Path lengkap file hasil foto terakhir.
    """
    # Pastikan folder penyimpanan ada
    Path(save_dir).mkdir(exist_ok=True)
    
    # Setup kamera
    picam2 = Picamera2()
    picam2.configure(picam2.create_still_configuration(main={"size": (640, 480)}))
    
    if preview:
        picam2.start_preview(Preview.QTGL)  # Hanya tampil kalau pakai HDMI monitor
    picam2.start()
    sleep(2)
    
    print("="*60)
    print("ANEMIA DETECTION - MANUAL CAPTURE")
    print("="*60)
    print("\n Camera ready!")
    print("Arahkan kamera ke MATA PASIEN")
    print(" Tekan ENTER untuk CAPTURE")
    print(" Tekan Ctrl+C untuk EXIT\n")
    
    counter = 1
    last_captured = None

    try:
        while True:
            input(f"\n[{counter}] Tekan ENTER untuk capture... ")
            
            # Countdown
            for t in [3, 2, 1]:
                print(f"📸 Capturing in {t}...")
                sleep(1)
            
            # Simpan hasil
            filename = f"conjunctiva_{counter}.jpg"
            filepath = os.path.join(save_dir, filename)
            picam2.capture_file(filepath)
            
            print(f"Gambar tersimpan: {filepath}")
            last_captured = filepath
            
            # Tanya mau lanjut atau berhenti
            cont = input("Ambil lagi? (y/n): ").lower().strip()
            if cont != 'y':
                break
            
            counter += 1

    except KeyboardInterrupt:
        print("\n🛑 Capture dihentikan oleh user.")
    finally:
        picam2.stop()
        if preview:
            picam2.stop_preview()
        print("Camera turned off")
    
    return last_captured



