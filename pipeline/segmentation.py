import cv2
import torch 
import numpy as np
from config import config
from .preprocessing import get_segmentation_preprocessing

def segment_conjunctiva(image, seg_model, device):
    """
    Segment conjunctiva from eye image
    
    Args:
        image: Original image (H, W, 3) BGR
        seg_model: Segmentation model
        device: torch device
    
    Returns:
        mask: Binary mask (H, W) with 0=background, 255=conjunctiva
        mask_overlay: Visualization with mask overlay
    """
    print("\n🔍 Step 1: Segmenting conjunctiva...")
    
    # Convert BGR to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    original_size = image_rgb.shape[:2]
    
    # Preprocess
    transform = get_segmentation_preprocessing()
    augmented = transform(image=image_rgb)
    image_tensor = augmented['image'].unsqueeze(0).to(device)
    
    # Inference
    with torch.no_grad():
        output = seg_model(image_tensor)
        pred_mask = torch.sigmoid(output)
        pred_mask = (pred_mask > config.SEG_THRESHOLD).float()
    
    # Post-process mask
    mask = pred_mask.squeeze().cpu().numpy()
    mask = cv2.resize(mask, (original_size[1], original_size[0]), 
                        interpolation=cv2.INTER_NEAREST)
    mask = (mask * 255).astype(np.uint8)
    
    # Create overlay for visualization
    mask_overlay = image.copy()
    mask_color = np.zeros_like(image)
    mask_color[:, :, 2] = mask  # Red channel for conjunctiva
    mask_overlay = cv2.addWeighted(mask_overlay, 0.7, mask_color, 0.3, 0)
    
    print(f" Segmentation complete")
    print(f"   Mask size: {mask.shape}")
    print(f"   Conjunctiva pixels: {np.sum(mask > 0)}")
    
    return mask, mask_overlay