import os
import sys
import datetime
import shutil
from typing import List, Tuple
import tkinter as tk
from tkinter import filedialog
from google.cloud import vision

# Suppress macOS-specific messages
if sys.platform == 'darwin':
    stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')

# If on macOS, restore stderr after imports
if sys.platform == 'darwin':
    sys.stderr = stderr


class ToothImage:
    def __init__(self, image_path: str, date: datetime.date):
        self.image_path = image_path
        self.date = date
        self.shade = None


def upload_image(upload_dir: str) -> str:
    """
    Open a file dialog for the user to select an image of their teeth.
    Returns the path to the uploaded image.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    file_path = filedialog.askopenfilename(
        title="Select a tooth image",
        filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
    )

    if file_path:
        filename = f"teeth_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(file_path)[1]}"
        destination = os.path.join(upload_dir, filename)
        shutil.copy2(file_path, destination)
        print(f"Image uploaded successfully to {destination}")
        return destination
    else:
        print("No file selected.")
        return None


def analyze_tooth_shade(image_path: str, client: vision.ImageAnnotatorClient) -> Tuple[int, int, int]:
    """
    Analyze the tooth shade using Google Cloud Vision API.
    Returns an RGB tuple representing the dominant color.
    """
    try:
        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)

        # Perform image properties analysis
        response = client.image_properties(image=image)
        props = response.image_properties_annotation

        if response.error.message:
            print(f"API Error: {response.error.message}")
            return (220, 220, 210)  # Default shade if API fails

        # Get the dominant color
        if props.dominant_colors.colors:
            dominant_color = props.dominant_colors.colors[0].color
            return (
                int(dominant_color.red),
                int(dominant_color.green),
                int(dominant_color.blue)
            )
        else:
            print("No dominant colors found in the image")
            return (220, 220, 210)

    except Exception as e:
        print(f"Error in analyzing image: {str(e)}")
        return (220, 220, 210)  # Default shade if an error occurs


def compare_shades(initial_shade: Tuple[int, int, int], current_shade: Tuple[int, int, int]) -> float:
    """
    Compare two shades and return a value indicating the change.
    Positive values indicate lightening, negative values indicate darkening.
    """

    # Calculate weighted brightness (human eyes are more sensitive to green)
    def weighted_brightness(shade):
        return shade[0] * 0.299 + shade[1] * 0.587 + shade[2] * 0.114

    initial_brightness = weighted_brightness(initial_shade)
    current_brightness = weighted_brightness(current_shade)
    return current_brightness - initial_brightness


def visualize_progress(images: List[ToothImage]):
    """
    Create a visualization of the user's teeth whitening progress.
    """
    print("\nWhitening Progress:")
    for i, img in enumerate(images):
        r, g, b = img.shade
        print(f"Image {i + 1} - Date: {img.date}, Shade: RGB({r}, {g}, {b})")
        brightness = compare_shades((220, 220, 210), img.shade)  # Compare to a standard white
        print(f"Relative brightness: {brightness:.2f}")


def main():
    # Set up Google Cloud Vision client
    try:
        client = vision.ImageAnnotatorClient()
    except Exception as e:
        print(f"Error initializing Google Cloud Vision client: {str(e)}")
        print("Make sure you have set up your Google Cloud credentials correctly.")
        return

    images = []
    upload_dir = "uploaded_images"
    os.makedirs(upload_dir, exist_ok=True)

    while True:
        image_path = upload_image(upload_dir)
        if image_path is None:
            continue

        current_date = datetime.date.today()

        tooth_image = ToothImage(image_path, current_date)
        tooth_image.shade = analyze_tooth_shade(image_path, client)

        images.append(tooth_image)

        if len(images) > 1:
            change = compare_shades(images[0].shade, tooth_image.shade)
            print(f"Shade change since first image: {change:.2f}")
            if change > 0:
                print("Your teeth appear to be getting whiter!")
            elif change < 0:
                print("Your teeth appear to be getting darker.")
            else:
                print("No significant change in tooth shade.")

        visualize_progress(images)

        if input("Upload another image? (y/n): ").lower() != 'y':
            break
            print("something")


if __name__ == "__main__":
    main()