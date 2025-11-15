import cv2
import numpy as np

def smooth_mask(mask, kernel_size=5):
    """
    Smooth mask edges dengan morphological operations
    """
    # Convert to uint8
    mask_uint8 = (mask * 255).astype(np.uint8)
    
    # Morphological closing (fill small holes)
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    mask_closed = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel_close)
    
    # Morphological opening (remove small noise)
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    mask_opened = cv2.morphologyEx(mask_closed, cv2.MORPH_OPEN, kernel_open)
    
    # Gaussian blur untuk smooth edges
    mask_smoothed = cv2.GaussianBlur(mask_opened, (kernel_size, kernel_size), 0)
    
    # Back to 0-1 range
    mask_smoothed = mask_smoothed.astype(np.float32) / 255.0
    
    return mask_smoothed

def refine_mask_edges(mask, feather_amount=3):
    """
    Refine edges dengan feathering (soft edges)
    """
    mask_uint8 = (mask * 255).astype(np.uint8)
    
    # Erode sedikit
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask_eroded = cv2.erode(mask_uint8, kernel, iterations=1)
    
    # Blur untuk soft edge
    mask_blurred = cv2.GaussianBlur(mask_eroded, (feather_amount*2+1, feather_amount*2+1), 0)
    
    return mask_blurred.astype(np.float32) / 255.0

def crop_segmented_region(image, mask, margin=15):
    """
    Crop image berdasarkan segmented mask dengan margin
    """
    # Convert mask ke uint8 binary
    if mask.max() <= 1.0:
        mask_binary = (mask > 0.5).astype(np.uint8)
    else:
        mask_binary = (mask > 127).astype(np.uint8)
    
    # Find contours
    contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        return None, None, None
    
    # Get bounding box of all contours
    x_min, y_min = image.shape[1], image.shape[0]
    x_max, y_max = 0, 0
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        x_min = min(x_min, x)
        y_min = min(y_min, y)
        x_max = max(x_max, x + w)
        y_max = max(y_max, y + h)
    
    # Add margin
    x_min = max(0, x_min - margin)
    y_min = max(0, y_min - margin)
    x_max = min(image.shape[1], x_max + margin)
    y_max = min(image.shape[0], y_max + margin)
    
    # Crop
    cropped_image = image[y_min:y_max, x_min:x_max]
    cropped_mask = mask[y_min:y_max, x_min:x_max]
    
    bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
    
    return cropped_image, cropped_mask, bbox

def crop_conjunctiva(image, mask, padding=20, remove_background=True, smooth_edges=True):
    """
    Crop conjunctiva region from image using mask
    SAMA SEPERTI extract_conjunctiva_smooth() di inference.py
    
    Args:
        image: Original image (H, W, 3) BGR
        mask: Binary mask (H, W) with values 0-255 or 0-1
        padding: Extra padding around bounding box (default 20)
        remove_background: Remove background (True = black background, False = keep original)
        smooth_edges: Apply smoothing to mask edges
    
    Returns:
        cropped: Cropped conjunctiva image with background removed
        bbox: Bounding box (x, y, w, h)
    """
    print("\n?? Step 2: Cropping conjunctiva area...")
    
    # Normalize mask to 0-1 range if needed
    if mask.max() > 1.0:
        mask = mask.astype(np.float32) / 255.0
    
    # Apply smoothing if enabled
    if smooth_edges:
        print("   Smoothing mask edges...")
        mask = smooth_mask(mask, kernel_size=5)
        mask = refine_mask_edges(mask, feather_amount=3)
    
    # Crop to segmented region
    cropped_img, cropped_mask, bbox = crop_segmented_region(image, mask, margin=padding)
    
    if cropped_img is None:
        raise ValueError("? No conjunctiva detected in mask!")
    
    # Remove background if enabled
    if remove_background:
        print("   Removing background...")
        # Create black background
        output = np.zeros_like(cropped_img)
        
        # Blend with soft edges (using mask as alpha)
        mask_3d = np.stack([cropped_mask] * 3, axis=2)
        output = (cropped_img * mask_3d + output * (1 - mask_3d)).astype(np.uint8)
    else:
        output = cropped_img
    
    print(f"? Crop complete")
    print(f"   Bounding box: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")
    print(f"   Cropped size: {output.shape}")
    
    return output, bbox
