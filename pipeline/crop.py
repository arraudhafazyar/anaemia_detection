import cv2

def crop_conjunctiva(image, mask, padding=20):
    """
    Crop conjunctiva region from image using mask
    
    Args:
        image: Original image (H, W, 3) BGR
        mask: Binary mask (H, W) with 0=background, 255=conjunctiva
        padding: Extra padding around bounding box
    
    Returns:
        cropped: Cropped conjunctiva image
        bbox: Bounding box (x, y, w, h)
    """
    print("\n Step 2: Cropping conjunctiva area...")
    
    # Find bounding box of mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        raise ValueError(" No conjunctiva detected in mask!")
    
    # Get largest contour (main conjunctiva area)
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Add padding
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(image.shape[1] - x, w + 2*padding)
    h = min(image.shape[0] - y, h + 2*padding)
    
    # Crop
    cropped = image[y:y+h, x:x+w]
    
    print(f" Crop complete")
    print(f"   Bounding box: x={x}, y={y}, w={w}, h={h}")
    print(f"   Cropped size: {cropped.shape}")
    
    return cropped, (x, y, w, h)