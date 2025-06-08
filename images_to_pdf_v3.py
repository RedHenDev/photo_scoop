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

def generate_spiral_positions(num_images):
    """Generate positions for images in a spiral pattern starting from center."""
    if num_images == 0:
        return []
    
    positions = []
    
    # Start at center (0, 0)
    positions.append((0, 0))
    
    if num_images == 1:
        return positions
    
    # Spiral outward using a proper algorithm
    x, y = 0, 0
    dx, dy = 1, 0  # Start moving right
    steps_in_direction = 1
    steps_taken = 0
    direction_changes = 0
    
    for i in range(1, num_images):
        # Move in current direction
        x += dx
        y += dy
        positions.append((x, y))
        steps_taken += 1
        
        # Check if we need to change direction
        if steps_taken == steps_in_direction:
            # Turn 90 degrees counter-clockwise
            dx, dy = -dy, dx
            direction_changes += 1
            steps_taken = 0
            
            # Increase steps every two direction changes
            if direction_changes % 2 == 0:
                steps_in_direction += 1
    
    return positions

def calculate_spiral_dimensions(num_images, available_width, available_height):
    """Calculate dimensions for spiral layout ensuring all images touch without gaps."""
    if num_images == 0:
        return 0, 0
    
    # Get spiral positions
    positions = generate_spiral_positions(num_images)
    
    # Find the bounds of the spiral
    min_x = min(pos[0] for pos in positions)
    max_x = max(pos[0] for pos in positions)
    min_y = min(pos[1] for pos in positions)
    max_y = max(pos[1] for pos in positions)
    
    # Calculate grid dimensions
    grid_width = max_x - min_x + 1
    grid_height = max_y - min_y + 1
    
    # Calculate cell size to fit available space
    cell_width = available_width / grid_width
    cell_height = available_height / grid_height
    
    # Use the smaller dimension to ensure everything fits
    cell_size = min(cell_width, cell_height)
    
    return cell_size, positions

def arrange_all_images_on_single_page(image_files, available_width, available_height):
    """Arrange ALL images in a touching spiral pattern starting from center."""
    num_images = len(image_files)
    if num_images == 0:
        return []
    
    print(f"Arranging {num_images} images in a spiral pattern")
    
    # Calculate spiral layout
    cell_size, positions = calculate_spiral_dimensions(num_images, available_width, available_height)
    
    # Find bounds for centering the spiral on the page
    min_x = min(pos[0] for pos in positions)
    max_x = max(pos[0] for pos in positions)
    min_y = min(pos[1] for pos in positions)
    max_y = max(pos[1] for pos in positions)
    
    # Calculate offset to center the spiral
    spiral_width = (max_x - min_x + 1) * cell_size
    spiral_height = (max_y - min_y + 1) * cell_size
    
    offset_x = (available_width - spiral_width) / 2 - min_x * cell_size
    offset_y = (available_height - spiral_height) / 2 - min_y * cell_size
    
    # Arrange images
    arranged_images = []
    for i, img_path in enumerate(image_files):
        if i >= len(positions):
            break
            
        grid_x, grid_y = positions[i]
        
        # Calculate actual position on page
        x = offset_x + grid_x * cell_size
        y = offset_y + grid_y * cell_size
        
        # Calculate image dimensions to fit exactly in cell (touching adjacent images)
        width, height, scale = calculate_image_dimensions(img_path, cell_size, cell_size)
        
        if width is not None and height is not None:
            # Center image within its cell
            cell_center_x = x + cell_size / 2
            cell_center_y = y + cell_size / 2
            
            final_x = cell_center_x - width / 2
            final_y = cell_center_y - height / 2
            
            arranged_images.append({
                'path': img_path,
                'x': final_x,
                'y': final_y,
                'width': width,
                'height': height,
                'scale': scale,
                'cell_size': cell_size
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
            print(f"  Added: {img_info['path'].name} (cell: {img_info['cell_size']:.0f}x{img_info['cell_size']:.0f})")
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
