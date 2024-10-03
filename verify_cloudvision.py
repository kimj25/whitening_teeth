
def verify_installation():
    try:
        from google.cloud import vision
        print("Google Cloud Vision library is successfully installed!")

        # Try to create a client (this won't work without credentials, but it verifies the import)
        try:
            client = vision.ImageAnnotatorClient()
            print("Successfully created ImageAnnotatorClient!")
        except Exception as e:
            print("Library installed, but client creation failed (this is expected without credentials)")
            print(f"Error: {str(e)}")

    except ImportError:
        print("Failed to import google.cloud.vision. Please check your installation.")


if __name__ == "__main__":
    verify_installation()