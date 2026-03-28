"""Google Photos dlt resources -- media items, albums."""

from typing import Any

import dlt
import pendulum


@dlt.resource(write_disposition="merge", primary_key="id")
def media_items(
    service: Any,
    start_date: str = "30 days ago",
) -> Any:
    """Yield photos and videos from the user's library."""
    if "days ago" in start_date:
        days = int(start_date.split()[0])
        start = pendulum.now().subtract(days=days).start_of("day")
    else:
        start = pendulum.parse(start_date).start_of("day")

    date_filter = {
        "dateFilter": {
            "ranges": [
                {
                    "startDate": {"year": start.year, "month": start.month, "day": start.day},
                    "endDate": {"year": 2099, "month": 12, "day": 31},
                }
            ]
        }
    }

    page_token = None
    while True:
        body = {**date_filter, "pageSize": 100}
        if page_token:
            body["pageToken"] = page_token

        result = service.mediaItems().search(body=body).execute()

        for item in result.get("mediaItems", []):
            metadata = item.get("mediaMetadata", {})
            yield {
                "id": item["id"],
                "filename": item.get("filename", ""),
                "mime_type": item.get("mimeType", ""),
                "creation_time": metadata.get("creationTime", ""),
                "width": int(metadata.get("width", 0)),
                "height": int(metadata.get("height", 0)),
                "media_type": "video" if "video" in metadata else "photo",
                "camera_make": metadata.get("photo", {}).get("cameraMake", ""),
                "camera_model": metadata.get("photo", {}).get("cameraModel", ""),
                "fps": metadata.get("video", {}).get("fps", 0.0),
                "description": item.get("description", ""),
                "product_url": item.get("productUrl", ""),
            }

        page_token = result.get("nextPageToken")
        if not page_token:
            break


@dlt.resource(write_disposition="replace")
def albums(service: Any) -> Any:
    """Yield all albums in the user's library."""
    page_token = None
    while True:
        params: dict[str, Any] = {"pageSize": 50}
        if page_token:
            params["pageToken"] = page_token

        result = service.albums().list(**params).execute()

        for album in result.get("albums", []):
            yield {
                "id": album["id"],
                "title": album.get("title", ""),
                "product_url": album.get("productUrl", ""),
                "media_items_count": int(album.get("mediaItemsCount", 0)),
                "cover_photo_base_url": album.get("coverPhotoBaseUrl", ""),
                "cover_photo_media_item_id": album.get("coverPhotoMediaItemId", ""),
            }

        page_token = result.get("nextPageToken")
        if not page_token:
            break
