#!/bin/sh
# Sync packages from GCS bucket to local directory on startup.
# If GCS_PACKAGES_BUCKET is not set, skip (local dev).
set -e

PACKAGES_DIR="/app/packages"
mkdir -p "$PACKAGES_DIR"

if [ -z "$GCS_PACKAGES_BUCKET" ]; then
    echo "GCS_PACKAGES_BUCKET not set, skipping sync"
    exit 0
fi

echo "Syncing packages from gs://$GCS_PACKAGES_BUCKET..."
python3 -c "
from google.cloud import storage
import os

bucket_name = os.environ['GCS_PACKAGES_BUCKET']
client = storage.Client()
bucket = client.bucket(bucket_name)
blobs = bucket.list_blobs()
count = 0
for blob in blobs:
    dest = os.path.join('$PACKAGES_DIR', blob.name)
    if not os.path.exists(dest):
        blob.download_to_filename(dest)
        count += 1
print(f'Synced {count} new packages from gs://{bucket_name}')
"
