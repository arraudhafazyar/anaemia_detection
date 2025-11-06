import time 
import cv2
from .segmentation import segment_conjunctiva
from .crop import crop_conjunctiva
from .classification import classify_anemia
from utils.save_results import save_pipeline_results
from utils.visualization import print_pipeline_summary

def main_pipeline(image_path, seg_model, class_model, device, 
                                save_results=False, output_dir="results"):
    """
    Complete pipeline: Segmentation → Crop → Classification
    
    Args:
        image_path: Path to input image
        seg_model: Segmentation model
        class_model: Classification model
        device: torch device
        save_results: Save intermediate results
        output_dir: Directory to save results
    
    Returns:
        dict: Complete results with all intermediate outputs
    """
    print("\n" + "="*60)
    print(" ANEMIA DETECTION PIPELINE")
    print("="*60)
    print(f"Input image: {image_path}")
    
    start_time = time.time()
    
    # Load image
    print("\n📸 Loading image...")
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    print(f" Image loaded: {image.shape}")
    
    # Step 1: Segment conjunctiva
    mask, mask_overlay = segment_conjunctiva(image, seg_model, device)
    
    # Step 2: Crop conjunctiva
    cropped, bbox = crop_conjunctiva(image, mask)
    
    # Step 3: Classify anemia
    result = classify_anemia(cropped, class_model, device)
    
    # Calculate total time
    total_time = time.time() - start_time
    
    # Compile results
    pipeline_result = {
        'input_image': image,
        'mask': mask,
        'mask_overlay': mask_overlay,
        'cropped': cropped,
        'bbox': bbox,
        'classification': result,
        'processing_time': total_time
    }
    
    # Save results
    if save_results:
        save_pipeline_results(pipeline_result, image_path, output_dir)
    
    # Print summary
    print_pipeline_summary(pipeline_result)
    
    return pipeline_result