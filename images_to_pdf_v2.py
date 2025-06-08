#!/usr/bin/env python3
"""
Images to A4 PDF Converter

This script takes all image files from a specified folder and arranges them
to fit on A4-sized PDF pages. It supports common image formats and automatically
handles layout optimization.

Requirements:
    pip install Pillow reportlab

Usage:
    python images_to_pdf.py /path/to/image/folder [output.pdf]
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import math

# A4 dimensions in points (72 points per inch)
A4_WIDTH, A4_HEIGHT = A4
MARGIN = 36  # 0.5 inch margin

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'}

def get_image_files(folder_path):
    """Get all supported image files from the specified folder."""
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    image_files = []
    for file_path in folder.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS:
            image_files.append(file_path)
    
    # Sort files naturally
    image_files.sort(key=lambda x: x.name.lower())
    return image_files

def calculate_image_dimensions(img_path, max_width, max_height):
    """Calculate the dimensions to fit image within the specified bounds while maintaining aspect ratio."""
    try:
        with Image.open(img_path) as img:
            orig_width, orig_height = img.size
            
        # Calculate scaling factor to fit within bounds
        width_ratio = max_width / orig_width
        height_ratio = max_height / orig_height
        scale_factor = min(width_ratio, height_ratio)
        
        new_width = orig_width * scale_factor
        new_height = orig_height * scale_factor
        
        return new_width, new_height, scale_factor
    except Exception as e:
        print(f"Error processing {img_path}: {e}")
        return None, None, None

def calculate_grid_layout(num_images):
    """Calculate optimal grid layout (rows x cols) for given number of images."""
    if num_images == 1:
        return 1, 1
    elif num_images == 2:
        return 1, 2
    elif num_images <= 4:
        return 2, 2
    elif num_images <= 6:
        return 2, 3
    elif num_images <= 9:
        return 3, 3
    elif num_images <= 12:
        return 3, 4
    elif num_images <= 16:
        return 4, 4
    elif num_images <= 20:
        return 4, 5
    elif num_images <= 25:
        return 5, 5
    else:
        # For very large numbers, calculate a roughly square grid
        cols = math.ceil(math.sqrt(num_images))
        rows = math.ceil(num_images / cols)
        return rows, cols

def arrange_all_images_on_single_page(image_files, available_width, available_height):
    """Arrange ALL images to fit on a single page using a grid layout."""
    num_images = len(image_files)
    if num_images == 0:
        return []
    
    # Calculate grid dimensions
    rows, cols = calculate_grid_layout(num_images)
    
    print(f"Arranging {num_images} images in a {rows}x{cols} grid")
    
    # Calculate spacing
    spacing = 5  # Small spacing between images
    total_spacing_width = (cols - 1) * spacing
    total_spacing_height = (rows - 1) * spacing
    
    # Calculate available space for each image
    cell_width = (available_width - total_spacing_width) / cols
    cell_height = (available_height - total_spacing_height) / rows
    
    # Arrange images in grid
    arranged_images = []
    for i, img_path in enumerate(image_files):
        row = i // cols
        col = i % cols
        
        # Calculate position
        x = col * (cell_width + spacing)
        y = available_height - (row + 1) * cell_height - row * spacing
        
        # Calculate image dimensions to fit in cell
        width, height, scale = calculate_image_dimensions(img_path, cell_width, cell_height)
        
        if width is not None and height is not None:
            # Center image within its cell
            cell_center_x = x + cell_width / 2
            cell_center_y = y + cell_height / 2
            
            final_x = cell_center_x - width / 2
            final_y = cell_center_y - height / 2
            
            arranged_images.append({
                'path': img_path,
                'x': final_x,
                'y': final_y,
                'width': width,
                'height': height,
                'scale': scale
            })
    
    return arranged_images

def create_pdf_from_images(image_files, output_path):
    """Create a single-page PDF with ALL images arranged to fit on one A4 page."""
    if not image_files:
        print("No image files found.")
        return
    
    print(f"Found {len(image_files)} image files")
    print(f"Creating single-page PDF: {output_path}")
    
    # Create PDF canvas
    c = canvas.Canvas(str(output_path), pagesize=A4)
    
    # Available space for images (accounting for margins)
    available_width = A4_WIDTH - 2 * MARGIN
    available_height = A4_HEIGHT - 2 * MARGIN
    
    # Arrange ALL images on a single page
    arranged_images = arrange_all_images_on_single_page(
        image_files, available_width, available_height
    )
    
    # Draw all images on the page
    added_count = 0
    for img_info in arranged_images:
        try:
            img_reader = ImageReader(str(img_info['path']))
            c.drawImage(img_reader, 
                       MARGIN + img_info['x'], 
                       MARGIN + img_info['y'], 
                       width=img_info['width'], 
                       height=img_info['height'])
            print(f"  Added: {img_info['path'].name} ({img_info['width']:.0f}x{img_info['height']:.0f})")
            added_count += 1
        except Exception as e:
            print(f"  Error adding {img_info['path'].name}: {e}")
    
    # Save the PDF
    c.save()
    print(f"PDF created successfully: {output_path}")
    print(f"Images added: {added_count}/{len(image_files)} on 1 page")
    
    if len(image_files) > 25:
        print(f"Note: With {len(image_files)} images, each image will be quite small.")
        print("Consider reducing the number of images for better visibility.")

def main():
    parser = argparse.ArgumentParser(description='Convert images in a folder to A4 PDF')
    parser.add_argument('folder', help='Path to folder containing images')
    parser.add_argument('output', nargs='?', default='images_output.pdf', 
                       help='Output PDF filename (default: images_output.pdf)')
    
    args = parser.parse_args()
    
    try:
        # Get all image files
        image_files = get_image_files(args.folder)
        
        if not image_files:
            print(f"No supported image files found in: {args.folder}")
            print(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
            return
        
        # Create PDF
        create_pdf_from_images(image_files, args.output)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
