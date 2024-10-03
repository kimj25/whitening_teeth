from google.cloud import vision

def test_credentials():
    try:
        client = vision.ImageAnnotatorClient()
        print("Successfully created client! Your credentials are working.")
        return True
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    test_credentials()