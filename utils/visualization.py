import cv2 
from config import config

def print_pipeline_summary(result):
    """Print pipeline summary"""
    classification = result['classification']
    
    print("\n" + "="*60)
    print("📊 PIPELINE RESULTS")
    print("="*60)
    
    print(f"\n⏱️ Processing Time: {result['processing_time']:.2f} seconds")
    
    print(f"\n🎯 FINAL PREDICTION:")
    print(f"   Result: {classification['class_name']}")
    print(f"   Confidence: {classification['confidence']*100:.2f}%")
    
    print(f"\n📊 Probabilities:")
    print(f"   Anemia: {classification['prob_anemia']*100:.2f}%")
    print(f"   Normal: {classification['prob_normal']*100:.2f}%")
    
    # Confidence warning
    if classification['confidence'] < config.CLASS_THRESHOLD:
        print(f"\n⚠️ WARNING: Low confidence (<{config.CLASS_THRESHOLD*100:.0f}%)")
        print(f"   Manual review recommended")
    
    # Interpretation
    print(f"\n💡 Interpretation:")
    if classification['class_name'] == 'Anemia':
        print(f"   ⚠️ Patient shows signs of ANEMIA")
        print(f"   → Recommend further medical examination")
        print(f"   → Check hemoglobin levels")
    else:
        print(f"   ✅ Patient appears NORMAL")
        print(f"   → No signs of anemia detected")
        print(f"   → Routine checkup recommended")
    
    print("="*60 + "\n")

def visualize_pipeline(result, show=True, save_path=None):
    """Visualize complete pipeline"""
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Original image
    axes[0, 0].imshow(cv2.cvtColor(result['input_image'], cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title('1. Original Image', fontsize=12, weight='bold')
    axes[0, 0].axis('off')
    
    # Mask overlay
    axes[0, 1].imshow(cv2.cvtColor(result['mask_overlay'], cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title('2. Segmentation (Conjunctiva)', fontsize=12, weight='bold')
    axes[0, 1].axis('off')
    
    # Cropped
    axes[1, 0].imshow(cv2.cvtColor(result['cropped'], cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title('3. Cropped Conjunctiva', fontsize=12, weight='bold')
    axes[1, 0].axis('off')
    
    # Classification result
    classification = result['classification']
    class_name = classification['class_name']
    confidence = classification['confidence']
    
    # Probability bars
    classes = ['Anemia', 'Normal']
    probs = [classification['prob_anemia'], classification['prob_normal']]
    colors = ['#FF6B6B', '#51CF66']
    
    bars = axes[1, 1].barh(classes, probs, color=colors, alpha=0.7, edgecolor='black')
    axes[1, 1].set_xlim([0, 1])
    axes[1, 1].set_xlabel('Probability', fontsize=11, weight='bold')
    axes[1, 1].set_title(f'4. Classification\n{class_name} ({confidence*100:.1f}%)', 
                        fontsize=12, weight='bold')
    axes[1, 1].grid(axis='x', alpha=0.3)
    
    # Add percentage labels
    for bar, prob in zip(bars, probs):
        width = bar.get_width()
        axes[1, 1].text(width, bar.get_y() + bar.get_height()/2, 
                       f'{prob*100:.1f}%',
                       ha='left', va='center', fontsize=10, weight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ Visualization saved: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()