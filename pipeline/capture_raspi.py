"""
Function: capture_conjunctiva()
Deskripsi:
Menangkap gambar konjungtiva dengan live preview di monitor
menggunakan Raspberry Pi Camera v3 (Picamera2).
"""

from picamera2 import Picamera2, Preview
from time import sleep
from pathlib import Path
import os
from datetime import datetime
import cv2

def capture_conjunctiva(save_dir="captures", show_preview=True, show_captured=True):
    """
    Capture gambar konjungtiva dengan live preview dan konfirmasi kualitas.
    
    Workflow:
    1. Live preview muncul di monitor
    2. User arahkan kamera ke mata pasien
    3. Tekan ENTER untuk capture
    4. Preview frozen + gambar ditampilkan dalam window OpenCV
    5. User konfirmasi: y (terima) / n (capture ulang)
    
    Args:
        save_dir (str): Folder penyimpanan
        show_preview (bool): Tampilkan live preview saat capturing
        show_captured (bool): Tampilkan hasil capture di OpenCV window untuk review
    
    Returns:
        str or None: Path file yang diterima, atau None jika dibatalkan
    """
    # Pastikan folder ada
    Path(save_dir).mkdir(exist_ok=True)
    
    print("="*60)
    print("🔬 ANEMIA DETECTION - CAPTURE KONJUNGTIVA")
    print("="*60)
    
    # Setup kamera
    try:
        picam2 = Picamera2()
        
        # Configuration untuk still capture
        config = picam2.create_still_configuration(
            main={"size": (640, 480)},
            buffer_count=2
        )
        picam2.configure(config)
        
        # Start preview di monitor (QTGL untuk hardware acceleration)
        if show_preview:
            try:
                picam2.start_preview(Preview.QTGL)
                print(" Live preview: AKTIF di monitor")
            except Exception as e:
                print(f"  Preview gagal: {e}")
                show_preview = False
        
        picam2.start()
        sleep(2)  # Warm-up
        
        print("\n Camera ready!")
        print("\n    INSTRUKSI:")
        print("   1. Arahkan kamera ke KONJUNGTIVA mata pasien")
        print("      (Bagian DALAM kelopak mata BAWAH yang berwarna merah/pink)")
        print("   2. Pastikan pencahayaan cukup terang")
        print("   3. Minta pasien membuka mata lebar dan lihat ke atas")
        print("   4. Tarik kelopak mata bawah dengan lembut")
        print("   5. Fokuskan kamera pada area konjungtiva\n")
        
    except Exception as e:
        print(f" Error initializing camera: {e}")
        print("   Troubleshooting:")
        print("   - Cek koneksi kamera ke Raspberry Pi")
        print("   - Pastikan kamera diaktifkan di raspi-config")
        print("   - Coba: sudo raspi-config → Interface → Camera → Enable")
        return None
    
    # Main capture loop
    attempt = 1
    temp_dir = os.path.join(save_dir, ".temp")
    Path(temp_dir).mkdir(exist_ok=True)
    
    try:
        while True:
            print(f"\n{'─'*60}")
            print(f"📷 Attempt #{attempt}")
            print(f"{'─'*60}")
            
            # Wait for user ready
            input("👉 Tekan ENTER ketika sudah siap capture... ")
            
            # Countdown untuk persiapan
            print("\n⏱️  Bersiap...", end=' ', flush=True)
            for t in [3, 2, 1]:
                print(f"{t}...", end=' ', flush=True)
                sleep(1)
            print("📸 SNAP!\n")
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"temp_{timestamp}.jpg"
            temp_filepath = os.path.join(temp_dir, temp_filename)
            
            # Capture image
            try:
                picam2.capture_file(temp_filepath)
                print(f"✅ Gambar dicapture")
                
            except Exception as e:
                print(f"❌ Gagal capture: {e}")
                retry = input("\n   Coba lagi? (y/n): ").lower().strip()
                if retry != 'y':
                    break
                attempt += 1
                continue
            
            # ==========================================
            # TAMPILKAN GAMBAR UNTUK REVIEW
            # ==========================================
            if show_captured:
                try:
                    # Load dan tampilkan di OpenCV window
                    img = cv2.imread(temp_filepath)
                    
                    if img is not None:
                        # Resize untuk display yang lebih besar (optional)
                        display_img = cv2.resize(img, (800, 600))
                        
                        # Add instruction text
                        cv2.putText(display_img, "Review Kualitas Gambar", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                                   1, (0, 255, 0), 2)
                        cv2.putText(display_img, "Tekan ESC atau Q untuk close window", 
                                   (10, 570), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.6, (255, 255, 255), 1)
                        
                        # Show image
                        cv2.imshow("Captured Image - Review", display_img)
                        cv2.waitKey(100)  # Brief pause untuk render window
                        
                        print("\n🖼️  Gambar ditampilkan di window terpisah")
                        print("   (Tutup window dengan ESC atau Q)")
                    
                except Exception as e:
                    print(f"⚠️  Tidak bisa menampilkan gambar: {e}")
                    print(f"   File tersimpan di: {temp_filepath}")
            
            # ==========================================
            # KONFIRMASI KUALITAS
            # ==========================================
            print("\n🔍 CHECKLIST KUALITAS:")
            print("   ✓ Apakah konjungtiva terlihat JELAS?")
            print("   ✓ Apakah pencahayaan CUKUP (tidak gelap/silau)?")
            print("   ✓ Apakah gambar TIDAK BLUR?")
            print("   ✓ Apakah area konjungtiva DOMINAN di gambar?")
            print("   ✓ Apakah mata pasien TERBUKA LEBAR?")
            
            while True:
                decision = input("\n❓ Apakah gambar ini cukup bagus? (y/n/c): ").lower().strip()
                
                if decision == 'y':
                    # ✅ TERIMA - Pindahkan dari temp ke final
                    final_filename = f"conjunctiva_{timestamp}.jpg"
                    final_filepath = os.path.join(save_dir, final_filename)
                    
                    os.rename(temp_filepath, final_filepath)
                    
                    # Close preview window
                    if show_captured:
                        cv2.destroyAllWindows()
                    
                    print("\n✅ GAMBAR DITERIMA!")
                    print(f"   📁 File: {final_filepath}")
                    print(f"   📏 Size: {os.path.getsize(final_filepath) / 1024:.1f} KB")
                    print("\n🎯 Siap untuk processing pipeline...\n")
                    
                    return final_filepath
                
                elif decision == 'n':
                    # ❌ TOLAK - Hapus dan capture ulang
                    print("❌ Gambar ditolak")
                    
                    # Close window
                    if show_captured:
                        cv2.destroyAllWindows()
                    
                    # Hapus file temp
                    try:
                        os.remove(temp_filepath)
                        print("   File temporary dihapus")
                    except:
                        pass
                    
                    retry = input("\n🔄 Capture ulang? (y/n): ").lower().strip()
                    if retry == 'y':
                        attempt += 1
                        break  # Kembali ke capture loop
                    else:
                        print("\n🛑 Capture dibatalkan")
                        return None
                
                elif decision == 'c':
                    # 🛑 CANCEL - Keluar tanpa save
                    print("\n🛑 Capture dibatalkan oleh user")
                    if show_captured:
                        cv2.destroyAllWindows()
                    try:
                        os.remove(temp_filepath)
                    except:
                        pass
                    return None
                
                else:
                    print("⚠️  Input tidak valid!")
                    print("   Ketik: y (terima) / n (capture ulang) / c (cancel)")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Capture dihentikan (Ctrl+C)")
        cv2.destroyAllWindows()
        return None
    
    finally:
        # Cleanup
        picam2.stop()
        if show_preview:
            try:
                picam2.stop_preview()
            except:
                pass
        
        cv2.destroyAllWindows()
        
        # Cleanup temp folder
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except:
            pass
        
        print("📷 Camera turned off\n")


# ============================================================
# HELPER: Capture Multiple Images
# ============================================================

def capture_multiple(save_dir="captures", max_images=5):
    """
    Capture beberapa gambar sekaligus untuk batch processing
    
    Args:
        save_dir (str): Folder penyimpanan
        max_images (int): Maksimal jumlah gambar
    
    Returns:
        list: List of accepted image paths
    """
    accepted_images = []
    
    print(f"\n📸 BATCH CAPTURE MODE (Max: {max_images} images)\n")
    
    for i in range(max_images):
        print(f"\n{'='*60}")
        print(f"IMAGE {i+1}/{max_images}")
        print(f"{'='*60}")
        
        image_path = capture_conjunctiva(save_dir)
        
        if image_path:
            accepted_images.append(image_path)
            print(f" Image {i+1} tersimpan")
        
        if i < max_images - 1:
            cont = input("\n  Capture image berikutnya? (y/n): ").lower().strip()
            if cont != 'y':
                break
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total images captured: {len(accepted_images)}")
    for idx, path in enumerate(accepted_images, 1):
        print(f"   {idx}. {path}")
    
    return accepted_images


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    print("\n🧪 TESTING CAPTURE FUNCTION\n")
    
    # Test single capture
    result = capture_conjunctiva(
        save_dir="test_captures",
        show_preview=True,
        show_captured=True
    )
    
    if result:
        print(f"\n SUCCESS: {result}")
    else:
        print(f"\n NO IMAGE CAPTURED")
# ```

# ## Fitur Tambahan:

# ### 1. **OpenCV Window untuk Review**
# - Gambar captured langsung muncul di window terpisah
# - Ukuran lebih besar (800x600) untuk review yang jelas
# - User bisa lihat detail sebelum decide

# ### 2. **Three-way Decision**
# ```
# y = terima gambar
# n = tolak dan capture ulang  
# c = cancel (keluar tanpa save)
# ```

# ### 3. **Temporary File System**
# - File disimpan di `.temp/` dulu
# - Kalau diterima → pindah ke folder final
# - Kalau ditolak → otomatis dihapus
# - Folder `.temp/` dibersihkan saat selesai

# ### 4. **Checklist Visual di Terminal**
# Membantu user evaluate kualitas:
# ```
# ✓ Konjungtiva terlihat JELAS?
# ✓ Pencahayaan CUKUP?
# ✓ Gambar TIDAK BLUR?
# ✓ Area konjungtiva DOMINAN?
# ✓ Mata TERBUKA LEBAR?