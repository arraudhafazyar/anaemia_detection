import os 
from pathlib import Path
import cv2

def save_pipeline_results(result, image_path, output_dir="results"):
    """Save all intermediate results"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base name
    base_name = Path(image_path).stem
    
    # Save images
    cv2.imwrite(f"{output_dir}/{base_name}_1_original.jpg", result['input_image'])
    cv2.imwrite(f"{output_dir}/{base_name}_2_mask_overlay.jpg", result['mask_overlay'])
    cv2.imwrite(f"{output_dir}/{base_name}_3_cropped.jpg", result['cropped'])
    
    # Save mask
    cv2.imwrite(f"{output_dir}/{base_name}_mask.png", result['mask'])
    
    print(f"\n💾 Results saved to: {output_dir}/")