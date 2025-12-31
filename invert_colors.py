#!/usr/bin/env python3
from PIL import Image, ImageOps

# Open the screenshot
print("Opening screenshot...")
img = Image.open('docker-docs-screenshot.png')

# Invert the colors
print("Inverting colors...")
inverted_img = ImageOps.invert(img.convert('RGB'))

# Save the inverted image
output_file = 'docker-docs-screenshot-inverted.png'
inverted_img.save(output_file)

print(f"Inverted screenshot saved as {output_file}")
