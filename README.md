# Teeth Whitening Tracker

A Streamlit app that tracks teeth whitening progress over time using AI-powered shade analysis via Google Cloud Vision.

Upload photos of your teeth on different days; the app extracts the dominant color, computes weighted brightness, and shows how your shade changes over time.

## Setup

```bash
pip install -r requirements.txt
```

### Google Cloud credentials

The app needs a Google Cloud service account with the Vision API enabled.

- **Local development:** set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON path, or add your account JSON to Streamlit secrets as `gcp_service_account`.
- **Streamlit Cloud:** add the service account JSON under the `gcp_service_account` key in [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Run

```bash
streamlit run app.py
```

## Usage

1. Upload a clear, front-facing photo of your teeth.
2. Click **Analyze Shade**.
3. Repeat on different days and compare progress.

For consistent results, keep lighting, camera distance, and angle the same between photos.
