import segmentation_models_pytorch as smp
from torchvision import transforms
import torch
import cv2
import numpy as np

def segment_conjunctiva(image, model, device):
    """
    Segment conjunctiva from image
    
    Args:
        image: BGR image (H, W, 3)
        model: Segmentation model
        device: torch device
    
    Returns:
        mask: Binary mask (H, W) with 0=background, 255=conjunctiva
        mask_overlay: Colored overlay image for visualization
    """
    print("\n?? Step 1: Segmenting conjunctiva...")
    
    # Save original size (width, height) for cv2.resize
    original_height, original_width = image.shape[:2]
    original_size = (original_width, original_height)
    
    # Resize to 640x640
    image_resized = cv2.resize(image, (640, 640), interpolation=cv2.INTER_AREA)
    
    # BGR to RGB
    image_rgb = cv2.cvtColor(image_resized, cv2.COLOR_BGR2RGB)
    
    # Get preprocessing function (same as training!)
    preprocessing_fn = smp.encoders.get_preprocessing_fn('mobilenet_v2', 'imagenet')
    
    # Apply preprocessing
    image_preprocessed = preprocessing_fn(image_rgb)
    
    # Convert to tensor
    input_tensor = torch.from_numpy(image_preprocessed).float()
    input_tensor = input_tensor.permute(2, 0, 1)  # HWC -> CHW
    input_tensor = input_tensor.unsqueeze(0).to(device)
    
    # Inference
    with torch.no_grad():
        output = model(input_tensor)
        probs = torch.sigmoid(output)
        mask_pred = (probs > 0.5).float()
    
    # Convert to numpy
    mask_np = mask_pred[0, 0].cpu().numpy()
    
    # Resize back to original size
    mask_resized = cv2.resize(mask_np, original_size, interpolation=cv2.INTER_NEAREST)
    
    # Convert to uint8
    mask = (mask_resized * 255).astype(np.uint8)
    
    # Create overlay for visualization
    mask_colored = np.zeros_like(image)
    mask_colored[mask > 127] = [0, 255, 0]  # Green overlay
    mask_overlay = cv2.addWeighted(image, 0.7, mask_colored, 0.3, 0)
    
    print(f"? Segmentation complete")
    print(f"   Image shape: {image.shape}")
    print(f"   Mask shape: {mask.shape}")
    print(f"   Mask area: {np.sum(mask > 127)} pixels ({np.sum(mask > 127) / mask.size * 100:.2f}%)")
    
    return mask, mask_overlay
