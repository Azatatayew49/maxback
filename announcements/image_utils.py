"""
Image compression utilities for handling large image uploads.
Automatically compresses images larger than 3MB while maintaining quality.
"""
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


def compress_image(image_field, max_size_mb=0.2):
    """
    Compress an image if it's larger than max_size_mb.
    
    Args:
        image_field: Django ImageField instance
        max_size_mb: Maximum file size in megabytes (default: 0.2MB = 200KB)
    
    Returns:
        Compressed image field or original if already small enough
    """
    max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
    
    # Check if image exists and has a size
    if not image_field or not hasattr(image_field, 'size'):
        return image_field
    
    # If image is already small enough, return as-is
    if image_field.size <= max_size_bytes:
        return image_field
    
    # Open the image
    img = Image.open(image_field)
    
    # Convert RGBA to RGB if necessary (for PNG with transparency)
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    
    # Get original format and filename
    img_format = img.format or 'JPEG'
    original_name = image_field.name
    
    # Start with high quality
    quality = 95
    output = BytesIO()
    
    # Iteratively reduce quality until size is acceptable
    while quality > 20:
        output.seek(0)
        output.truncate()
        
        # Save with current quality
        img.save(output, format=img_format, quality=quality, optimize=True)
        
        # Check size
        if output.tell() <= max_size_bytes:
            break
        
        # Reduce quality for next iteration
        quality -= 5
    
    # If still too large after quality reduction, resize the image
    if output.tell() > max_size_bytes:
        # Calculate new dimensions (reduce by 20% each iteration)
        width, height = img.size
        while output.tell() > max_size_bytes and width > 800:
            width = int(width * 0.8)
            height = int(height * 0.8)
            
            # Resize image
            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
            
            output.seek(0)
            output.truncate()
            img_resized.save(output, format=img_format, quality=quality, optimize=True)
    
    output.seek(0)
    
    # Create new InMemoryUploadedFile
    compressed_image = InMemoryUploadedFile(
        output,
        'ImageField',
        original_name,
        f'image/{img_format.lower()}',
        sys.getsizeof(output),
        None
    )
    
    return compressed_image
