import torch 
import segmentation_models_pytorch as smp
import os
import torch.nn as nn 

class SegmentationModel(nn.Module):
    """LinkNet for conjunctiva segmentation"""
    def __init__(self):
        super(SegmentationModel, self).__init__()
        self.model = smp.Linknet(
            encoder_name='mobilenet_v2',
            encoder_weights=None,  # Will load from checkpoint
            in_channels=3,
            classes=1,
            activation=None
        )
    
    def forward(self, x):
        return self.model(x)

def load_segmentation_model(model_path, device):
    """Load segmentation model"""
    print(f"Loading segmentation model from: {model_path}")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Segmentation model not found: {model_path}")
    
    model = SegmentationModel().to(device)
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    print("Segmentation model loaded")
    return model
