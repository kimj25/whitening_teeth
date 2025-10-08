import streamlit as st
import os
import datetime
import json
from typing import List, Tuple, Dict
from google.cloud import vision
from PIL import Image
import io

# Page configuration
st.set_page_config(
    page_title="Teeth Whitening Tracker",
    page_icon="🦷",
    layout="wide"
)

# Initialize session state
if 'images' not in st.session_state:
    st.session_state.images = []

if 'upload_dir' not in st.session_state:
    st.session_state.upload_dir = "uploaded_images"
    os.makedirs(st.session_state.upload_dir, exist_ok=True)


def get_vision_client():
    """Initialize Google Cloud Vision client"""
    try:
        # For Streamlit Cloud, credentials should be in secrets
        if 'gcp_service_account' in st.secrets:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            return vision.ImageAnnotatorClient(credentials=credentials)
        else:
            # For local development with GOOGLE_APPLICATION_CREDENTIALS
            return vision.ImageAnnotatorClient()
    except Exception as e:
        st.error(f"Error initializing Google Cloud Vision: {str(e)}")
        return None


def analyze_tooth_shade(image_bytes: bytes, client: vision.ImageAnnotatorClient) -> Tuple[int, int, int]:
    """
    Analyze the tooth shade using Google Cloud Vision API.
    Returns an RGB tuple representing the dominant color.
    """
    try:
        image = vision.Image(content=image_bytes)
        response = client.image_properties(image=image)
        props = response.image_properties_annotation

        if response.error.message:
            st.error(f"API Error: {response.error.message}")
            return (220, 220, 210)

        if props.dominant_colors.colors:
            dominant_color = props.dominant_colors.colors[0].color
            return (
                int(dominant_color.red),
                int(dominant_color.green),
                int(dominant_color.blue)
            )
        else:
            st.warning("No dominant colors found in the image")
            return (220, 220, 210)

    except Exception as e:
        st.error(f"Error analyzing image: {str(e)}")
        return (220, 220, 210)


def weighted_brightness(shade: Tuple[int, int, int]) -> float:
    """Calculate weighted brightness (human eye sensitivity)"""
    return shade[0] * 0.299 + shade[1] * 0.587 + shade[2] * 0.114


def compare_shades(initial_shade: Tuple[int, int, int], current_shade: Tuple[int, int, int]) -> float:
    """
    Compare two shades and return brightness difference.
    Positive values indicate lightening, negative values indicate darkening.
    """
    initial_brightness = weighted_brightness(initial_shade)
    current_brightness = weighted_brightness(current_shade)
    return current_brightness - initial_brightness


def main():
    st.title("🦷 Teeth Whitening Tracker")
    st.markdown("Track your teeth whitening progress over time using AI-powered shade analysis")

    # Sidebar for instructions
    with st.sidebar:
        st.header("📋 Instructions")
        st.markdown("""
        1. Upload a clear photo of your teeth
        2. Make sure lighting is consistent
        3. Take photos from the same angle
        4. Track your progress over time
        
        **Tips for best results:**
        - Use natural lighting
        - Keep camera distance consistent
        - Take photos at the same time of day
        """)

    # Initialize client
    client = get_vision_client()
    
    if client is None:
        st.error("⚠️ Google Cloud Vision API is not configured. Please add your credentials.")
        st.info("For Streamlit Cloud deployment, add your GCP service account JSON to Streamlit Secrets.")
        return

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a photo of your teeth",
        type=['png', 'jpg', 'jpeg', 'bmp'],
        help="Upload a clear photo of your teeth for shade analysis"
    )

    if uploaded_file is not None:
        # Display the uploaded image
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📸 Uploaded Image")
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)

        # Analyze button
        if st.button("🔍 Analyze Shade", type="primary"):
            with st.spinner("Analyzing tooth shade..."):
                # Get image bytes
                image_bytes = uploaded_file.getvalue()
                
                # Analyze shade
                shade = analyze_tooth_shade(image_bytes, client)
                
                # Create image record
                image_record = {
                    'date': datetime.date.today().isoformat(),
                    'shade': shade,
                    'brightness': weighted_brightness(shade)
                }
                
                # Add to session state
                st.session_state.images.append(image_record)
                
                with col2:
                    st.subheader("🎨 Analysis Results")
                    st.markdown(f"**Shade (RGB):** {shade[0]}, {shade[1]}, {shade[2]}")
                    st.markdown(f"**Brightness:** {image_record['brightness']:.2f}")
                    
                    # Show color swatch
                    st.markdown("**Dominant Color:**")
                    color_hex = f"#{shade[0]:02x}{shade[1]:02x}{shade[2]:02x}"
                    st.markdown(
                        f'<div style="width:100px;height:100px;background-color:{color_hex};'
                        f'border:2px solid #ccc;border-radius:10px;"></div>',
                        unsafe_allow_html=True
                    )

    # Display progress
    if len(st.session_state.images) > 0:
        st.divider()
        st.header("📊 Your Progress")
        
        # Progress metrics
        if len(st.session_state.images) > 1:
            first_shade = tuple(st.session_state.images[0]['shade'])
            latest_shade = tuple(st.session_state.images[-1]['shade'])
            change = compare_shades(first_shade, latest_shade)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Images", len(st.session_state.images))
            
            with col2:
                st.metric("Brightness Change", f"{change:.2f}")
            
            with col3:
                if change > 5:
                    st.success("✨ Getting Whiter!")
                elif change < -5:
                    st.warning("⚠️ Getting Darker")
                else:
                    st.info("➖ No Significant Change")
        
        # Display all records
        st.subheader("📅 History")
        for i, record in enumerate(reversed(st.session_state.images)):
            with st.expander(f"Image {len(st.session_state.images) - i} - {record['date']}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    shade = tuple(record['shade'])
                    color_hex = f"#{shade[0]:02x}{shade[1]:02x}{shade[2]:02x}"
                    st.markdown(
                        f'<div style="width:80px;height:80px;background-color:{color_hex};'
                        f'border:2px solid #ccc;border-radius:10px;"></div>',
                        unsafe_allow_html=True
                    )
                
                with col2:
                    st.markdown(f"**RGB:** {shade[0]}, {shade[1]}, {shade[2]}")
                    st.markdown(f"**Brightness:** {record['brightness']:.2f}")
                    
                    if i < len(st.session_state.images) - 1:
                        prev_record = list(reversed(st.session_state.images))[i + 1]
                        prev_shade = tuple(prev_record['shade'])
                        change = compare_shades(prev_shade, shade)
                        st.markdown(f"**Change from previous:** {change:+.2f}")
        
        # Clear history button
        if st.button("🗑️ Clear History"):
            st.session_state.images = []
            st.rerun()


if __name__ == "__main__":
    main()