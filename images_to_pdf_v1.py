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

def arrange_images_on_page(image_files, start_idx, available_width, available_height):
    """Determine how many images can fit on the current page and their layout."""
    page_images = []
    current_idx = start_idx
    
    # Try to fit images in a grid layout
    # Start with trying to fit images in rows
    remaining_height = available_height
    
    while current_idx < len(image_files) and remaining_height > 50:  # Minimum height threshold
        row_images = []
        row_height = 0
        remaining_width = available_width
        
        # Try to fit images in the current row
        while current_idx < len(image_files) and remaining_width > 50:  # Minimum width threshold
            img_path = image_files[current_idx]
            
            # Calculate dimensions for this image to fit in remaining space
            max_img_width = min(remaining_width, available_width * 0.8)  # Don't make images too wide
            max_img_height = min(remaining_height, available_height * 0.6)  # Don't make images too tall
            
            width, height, scale = calculate_image_dimensions(img_path, max_img_width, max_img_height)
            
            if width is None:
                current_idx += 1
                continue
                
            # Check if image fits in remaining row space
            if width <= remaining_width:
                row_images.append({
                    'path': img_path,
                    'width': width,
                    'height': height,
                    'scale': scale
                })
                remaining_width -= width + 10  # Add small spacing between images
                row_height = max(row_height, height)
                current_idx += 1
            else:
                break
        
        # If we have images in this row and enough height, add them to the page
        if row_images and row_height <= remaining_height:
            page_images.append(row_images)
            remaining_height -= row_height + 10  # Add spacing between rows
        else:
            break
    
    return page_images, current_idx

def create_pdf_from_images(image_files, output_path):
    """Create a PDF with all images arranged on A4 pages."""
    if not image_files:
        print("No image files found.")
        return
    
    print(f"Found {len(image_files)} image files")
    print(f"Creating PDF: {output_path}")
    
    # Create PDF canvas
    c = canvas.Canvas(str(output_path), pagesize=A4)
    
    # Available space for images (accounting for margins)
    available_width = A4_WIDTH - 2 * MARGIN
    available_height = A4_HEIGHT - 2 * MARGIN
    
    current_idx = 0
    page_num = 1
    
    while current_idx < len(image_files):
        print(f"Processing page {page_num}...")
        
        # Arrange images for current page
        page_images, next_idx = arrange_images_on_page(
            image_files, current_idx, available_width, available_height
        )
        
        if not page_images:
            # If no images fit, try with a single large image
            img_path = image_files[current_idx]
            width, height, scale = calculate_image_dimensions(
                img_path, available_width, available_height
            )
            
            if width is not None:
                # Center the image on the page
                x = MARGIN + (available_width - width) / 2
                y = MARGIN + (available_height - height) / 2
                
                try:
                    img_reader = ImageReader(str(img_path))
                    c.drawImage(img_reader, x, y, width=width, height=height)
                    print(f"  Added: {img_path.name}")
                except Exception as e:
                    print(f"  Error adding {img_path.name}: {e}")
            
            current_idx += 1
        else:
            # Draw all images on the current page
            current_y = A4_HEIGHT - MARGIN
            
            for row in page_images:
                # Calculate row width to center it
                row_width = sum(img['width'] for img in row) + (len(row) - 1) * 10
                start_x = MARGIN + (available_width - row_width) / 2
                
                # Find the maximum height in this row
                row_height = max(img['height'] for img in row)
                current_y -= row_height
                
                current_x = start_x
                for img_info in row:
                    try:
                        # Center image vertically in the row
                        img_y = current_y + (row_height - img_info['height']) / 2
                        
                        img_reader = ImageReader(str(img_info['path']))
                        c.drawImage(img_reader, current_x, img_y, 
                                  width=img_info['width'], height=img_info['height'])
                        print(f"  Added: {img_info['path'].name}")
                        
                        current_x += img_info['width'] + 10
                    except Exception as e:
                        print(f"  Error adding {img_info['path'].name}: {e}")
                
                current_y -= 10  # Spacing between rows
            
            current_idx = next_idx
        
        # Start new page if there are more images
        if current_idx < len(image_files):
            c.showPage()
            page_num += 1
    
    # Save the PDF
    c.save()
    print(f"PDF created successfully: {output_path}")
    print(f"Total pages: {page_num}")

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
