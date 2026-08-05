import datetime
import os
from io import BytesIO
from typing import Optional, Tuple

import streamlit as st
from google.cloud import vision
from PIL import Image

# Fallback shade used when analysis fails or no colors are found
DEFAULT_SHADE = (220, 220, 210)

st.set_page_config(
    page_title="Teeth Whitening Tracker",
    page_icon="🦷",
    layout="wide",
)

if "images" not in st.session_state:
    st.session_state.images = []

if "upload_dir" not in st.session_state:
    st.session_state.upload_dir = "uploaded_images"
    os.makedirs(st.session_state.upload_dir, exist_ok=True)


def get_vision_client() -> Optional[vision.ImageAnnotatorClient]:
    """Initialize the Google Cloud Vision client."""
    credentials = None
    try:
        # Streamlit Cloud: credentials come from Secrets
        if "gcp_service_account" in st.secrets:
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
    except Exception:
        pass  # No secrets file; fall back to GOOGLE_APPLICATION_CREDENTIALS

    try:
        # Local development: GOOGLE_APPLICATION_CREDENTIALS
        return vision.ImageAnnotatorClient(credentials=credentials)
    except Exception as e:
        st.error(f"Error initializing Google Cloud Vision: {e}")
        return None


MOUTH_LANDMARKS = ("MOUTH_LEFT", "MOUTH_RIGHT", "UPPER_LIP_TOP", "LOWER_LIP_BOTTOM")


def crop_to_mouth(
    image_bytes: bytes, client: vision.ImageAnnotatorClient
) -> Optional[bytes]:
    """Crop the image to the mouth region using Vision face landmarks."""
    try:
        image = vision.Image(content=image_bytes)
        response = client.face_detection(image=image)

        if response.error.message:
            st.error(f"API Error: {response.error.message}")
            return None
        if not response.face_annotations:
            st.warning("No face detected; analyzing the full image")
            return None

        landmarks = {
            lnd.type_.name: lnd.position
            for lnd in response.face_annotations[0].landmarks
        }
        missing = [key for key in MOUTH_LANDMARKS if key not in landmarks]
        if missing:
            st.warning(
                f"Missing mouth landmarks ({', '.join(missing)}); "
                "analyzing the full image"
            )
            return None

        img = Image.open(BytesIO(image_bytes))
        width, height = img.size

        x0 = min(landmarks["MOUTH_LEFT"].x, landmarks["MOUTH_RIGHT"].x) * width
        x1 = max(landmarks["MOUTH_LEFT"].x, landmarks["MOUTH_RIGHT"].x) * width
        y0 = min(landmarks["UPPER_LIP_TOP"].y, landmarks["LOWER_LIP_BOTTOM"].y) * height
        y1 = max(landmarks["UPPER_LIP_TOP"].y, landmarks["LOWER_LIP_BOTTOM"].y) * height

        pad_x = (x1 - x0) * 0.05
        pad_y = (y1 - y0) * 0.05
        x0, x1 = max(0, int(x0 - pad_x)), min(width, int(x1 + pad_x))
        y0, y1 = max(0, int(y0 - pad_y)), min(height, int(y1 + pad_y))

        if x1 - x0 < 10 or y1 - y0 < 10:
            st.warning("Mouth region too small; analyzing the full image")
            return None

        crop = img.crop((x0, y0, x1, y1))
        buf = BytesIO()
        crop.save(buf, format="JPEG")
        return buf.getvalue()

    except Exception as e:
        st.error(f"Error cropping mouth: {e}")
        return None


def analyze_tooth_shade(
    image_bytes: bytes, client: vision.ImageAnnotatorClient
) -> Tuple[int, int, int]:
    """Return the dominant RGB color of the image as the tooth shade."""
    try:
        image = vision.Image(content=image_bytes)
        response = client.image_properties(image=image)
        props = response.image_properties_annotation

        if response.error.message:
            st.error(f"API Error: {response.error.message}")
            return DEFAULT_SHADE

        if props.dominant_colors.colors:
            color = props.dominant_colors.colors[0].color
            return int(color.red), int(color.green), int(color.blue)

        st.warning("No dominant colors found in the image")
        return DEFAULT_SHADE

    except Exception as e:
        st.error(f"Error analyzing image: {e}")
        return DEFAULT_SHADE


def weighted_brightness(shade: Tuple[int, int, int]) -> float:
    """Calculate brightness weighted by human eye sensitivity."""
    return shade[0] * 0.299 + shade[1] * 0.587 + shade[2] * 0.114


def compare_shades(
    initial_shade: Tuple[int, int, int], current_shade: Tuple[int, int, int]
) -> float:
    """Return the brightness difference. Positive = lighter, negative = darker."""
    return weighted_brightness(current_shade) - weighted_brightness(initial_shade)


def color_swatch(shade: Tuple[int, int, int], size: int = 100) -> str:
    """Return HTML for a rounded color swatch of the given RGB shade."""
    hex_color = f"#{shade[0]:02x}{shade[1]:02x}{shade[2]:02x}"
    return (
        f'<div style="width:{size}px;height:{size}px;background-color:{hex_color};'
        f'border:2px solid #ccc;border-radius:10px;"></div>'
    )


def main():
    st.title("🦷 Teeth Whitening Tracker")
    st.markdown("Track your teeth whitening progress over time using AI-powered shade analysis")

    with st.sidebar:
        st.header("📋 Instructions")
        st.markdown(
            """
            1. Upload a clear photo of your teeth
            2. Make sure lighting is consistent
            3. Take photos from the same angle
            4. Track your progress over time

            **Tips for best results:**
            - Use natural lighting
            - Keep camera distance consistent
            - Take photos at the same time of day
            """
        )

    client = get_vision_client()
    if client is None:
        st.error("⚠️ Google Cloud Vision API is not configured. Please add your credentials.")
        st.info("For Streamlit Cloud deployment, add your GCP service account JSON to Streamlit Secrets.")
        return

    uploaded_file = st.file_uploader(
        "Upload a photo of your teeth",
        type=["png", "jpg", "jpeg", "bmp"],
        help="Upload a clear photo of your teeth for shade analysis",
    )

    if uploaded_file is not None:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📸 Uploaded Image")
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)

        if st.button("🔍 Analyze Shade", type="primary"):
            with st.spinner("Analyzing tooth shade..."):
                region_bytes = crop_to_mouth(uploaded_file.getvalue(), client)
                shade = analyze_tooth_shade(
                    region_bytes or uploaded_file.getvalue(), client
                )
                record = {
                    "date": datetime.date.today().isoformat(),
                    "shade": shade,
                    "brightness": weighted_brightness(shade),
                }
                st.session_state.images.append(record)

                with col2:
                    st.subheader("🎨 Analysis Results")
                    if region_bytes is not None:
                        st.markdown("**Analyzed Region:**")
                        st.image(region_bytes, width=200)
                    st.markdown(f"**Shade (RGB):** {shade[0]}, {shade[1]}, {shade[2]}")
                    st.markdown(f"**Brightness:** {record['brightness']:.2f}")
                    st.markdown("**Dominant Color:**")
                    st.markdown(color_swatch(shade), unsafe_allow_html=True)

    if st.session_state.images:
        st.divider()
        st.header("📊 Your Progress")

        if len(st.session_state.images) > 1:
            first_shade = tuple(st.session_state.images[0]["shade"])
            latest_shade = tuple(st.session_state.images[-1]["shade"])
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

        st.subheader("📅 History")
        for i, record in enumerate(reversed(st.session_state.images)):
            with st.expander(f"Image {len(st.session_state.images) - i} - {record['date']}"):
                col1, col2 = st.columns([1, 2])

                with col1:
                    shade = tuple(record["shade"])
                    st.markdown(color_swatch(shade, size=80), unsafe_allow_html=True)

                with col2:
                    st.markdown(f"**RGB:** {shade[0]}, {shade[1]}, {shade[2]}")
                    st.markdown(f"**Brightness:** {record['brightness']:.2f}")

                    if i < len(st.session_state.images) - 1:
                        prev_shade = tuple(
                            list(reversed(st.session_state.images))[i + 1]["shade"]
                        )
                        change = compare_shades(prev_shade, shade)
                        st.markdown(f"**Change from previous:** {change:+.2f}")

        if st.button("🗑️ Clear History"):
            st.session_state.images = []
            st.rerun()


if __name__ == "__main__":
    main()
