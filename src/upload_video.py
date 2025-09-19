import os
import json
import time
from shutil import copyfile
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime, timedelta

# The file containing your credentials
CLIENT_SECRETS_FILE = "client_secret_2_175796165599-opm7rn4umhi37gq2jsoa9fpglu6dm731.apps.googleusercontent.com.json"

# The scope defines what your application is allowed to do.
# 'https://www.googleapis.com/auth/youtube.upload' grants permission to upload videos.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


def get_authenticated_service():
    """Authenticates the user and returns the YouTube API service object."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no valid credentials, initiate the OAuth 2.0 flow.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run.
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def upload_video(
    youtube, file_path, thumbnail_path, title, description, tags, category_id, privacy_status, publish_at=None
):
    """Uploads a video to YouTube and returns the video ID."""
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "madeForKids": False,
            "selfDeclaredMadeForKids": True,
            "hasCustomThumbnail": True,
        },
        "status": {"privacyStatus": privacy_status},
    }

    if publish_at:
        request_body["status"]["publishAt"] = publish_at

    media_file = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    response = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media_file).execute()

    youtube.thumbnails().set(videoId=response["id"], media_body=MediaFileUpload(thumbnail_path)).execute()

    return response["id"]


if __name__ == "__main__":
    publish_datetime = datetime(2025, 9, 24, 10, 0, 0)
    youtube_service = get_authenticated_service()
    for folder in os.listdir("Output"):
        if folder in ["Archive", "n1", "n2", "n3", "n4", "n5"]:
            continue
        folder_path = os.path.join("Output", folder)
        VIDEO_TITLE = ""
        VIDEO_DESCRIPTION = ""
        VIDEO_TAGS = ["JLPT", "Japanese", "Vocabulary"]
        VIDEO_FILE_PATH = ""
        THUMBNAIL_FILE_PATH = ""
        VIDEO_CATEGORY_ID = "27"
        VIDEO_PRIVACY_STATUS = "private"
        PUBLISH_AT = None
        json_file_path = ""
        for file in os.listdir(folder_path):
            if file.endswith(".mp4"):
                VIDEO_FILE_PATH = os.path.join(folder_path, file)
                VIDEO_TITLE = file[:-4] + " NEW"
            elif file.endswith(".jpg"):
                THUMBNAIL_FILE_PATH = os.path.join(folder_path, file)
            elif file.endswith(".json"):
                json_file_path = os.path.join(folder_path, file)
                with open(json_file_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    VIDEO_DESCRIPTION = (
                        f"https://jvdict.streamlit.app/v?w={file[:-5]}\n"
                        + metadata["explanations"]["youtube_description"]
                    )
                    publish_datetime += timedelta(days=1)
                    PUBLISH_AT = publish_datetime.isoformat() + "Z"
        print(f"{VIDEO_TITLE} - {PUBLISH_AT} - {VIDEO_FILE_PATH} - {THUMBNAIL_FILE_PATH}")
        video_id = upload_video(
            youtube_service,
            VIDEO_FILE_PATH,
            THUMBNAIL_FILE_PATH,
            VIDEO_TITLE,
            VIDEO_DESCRIPTION,
            VIDEO_TAGS,
            VIDEO_CATEGORY_ID,
            VIDEO_PRIVACY_STATUS,
            PUBLISH_AT,
        )

        print(f"Video uploaded successfully! Video ID: {video_id}")
        with open(json_file_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            metadata["youtube_link"] = f"https://youtu.be/{video_id}"
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        copyfile(json_file_path, os.path.join("resources", "words", os.path.basename(json_file_path)))

        time.sleep(15)  # To avoid hitting rate limits
