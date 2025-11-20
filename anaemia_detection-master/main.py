import os
import time
import lgpio

from config import config
from models import load_classification_model, load_segmentation_model
from pipeline import main_pipeline, capture_conjunctiva
from utils import visualize_pipeline, print_pipeline_summary


# LED SETUP
LED_PIN = 17  # Ganti sesuai pin LED kamu
chip = lgpio.gpiochip_open(0)                      # open gpio chip
lgpio.gpio_claim_output(chip, LED_PIN, 0)          # set as output, default OFF



def main():
    """Main function for testing"""
    print("\n" + " "*30)
    print("RASPBERRY PI - ANEMIA DETECTION SYSTEM")
    print(" "*30)
    
    image_path = capture_conjunctiva(
        save_dir="patient_images",
        show_preview=True,
        show_captured=True
    )
    
    if not image_path:
        print("\n Tidak ada gambar yang diambil.")
        print("   Capture dibatalkan atau gagal.")
        return
    
    
    print(f"\n Gambar berhasil dicapture: {image_path}")
    print(f"   Size: {os.path.getsize(image_path) / 1024:.1f} KB")

    if not os.path.exists(config.SEGMENTATION_MODEL):
        print(f"Segmentation model not found: {config.SEGMENTATION_MODEL}")
        return
    
    if not os.path.exists(config.CLASSIFICATION_MODEL):
        print(f" Classification model not found: {config.CLASSIFICATION_MODEL}")
        return
    
    print("\n Loading models...")
    seg_model = load_segmentation_model(config.SEGMENTATION_MODEL, config.DEVICE)
    class_model = load_classification_model(config.CLASSIFICATION_MODEL, config.DEVICE)
    
    
    if os.path.exists(image_path):
        result = main_pipeline(
            image_path,
            seg_model,
            class_model,
            config.DEVICE,
            save_results=True,
            output_dir="results"
        )
        
        # LED on for 5 second
        print("\n💡 LED ON for 5 seconds...")
        lgpio.gpio_write(chip, LED_PIN, 1)
        time.sleep(5)
        lgpio.gpio_write(chip, LED_PIN, 0)
        print("💡 LED OFF")
        
        # Visualize
        visualize_pipeline(result, show=True, save_path="results/pipeline_visualization.png")

        
    else:
        print("Not found, Please provide a valid image path")
    
    print("\n Pipeline done")


if __name__ == "__main__":
    try:
        main()
    finally:
        lgpio.gpiochip_close(chip)   
