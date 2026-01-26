"""
Google Cloud Storage utility for persistent file storage.
Uses same credentials as BigQuery (GOOGLE_APPLICATION_CREDENTIALS_JSON).

This module provides GCS storage capabilities for JustData apps to persist
data across Cloud Run container instances.
"""
import json
import os
from typing import Any, Optional


def get_gcs_client():
    """
    Get authenticated GCS client using existing BigQuery credentials.

    Returns:
        google.cloud.storage.Client: Authenticated GCS client
    """
    from google.cloud import storage
    from google.oauth2 import service_account

    creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if creds_json:
        # Clean up the credentials string if needed
        creds_json = creds_json.strip()
        if (creds_json.startswith('"') and creds_json.endswith('"')) or \
           (creds_json.startswith("'") and creds_json.endswith("'")):
            creds_json = creds_json[1:-1].strip()

        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        return storage.Client(credentials=credentials, project=creds_dict.get('project_id'))

    # Fall back to default credentials (for local development with gcloud auth)
    return storage.Client()


def get_bucket(bucket_name: Optional[str] = None):
    """
    Get the specified GCS bucket or the default MergerMeter output bucket.

    Args:
        bucket_name: Optional bucket name. Defaults to GCS_BUCKET_NAME env var
                     or 'justdata-mergermeter-output'.

    Returns:
        google.cloud.storage.Bucket: GCS bucket object
    """
    client = get_gcs_client()
    if bucket_name is None:
        bucket_name = os.environ.get('GCS_BUCKET_NAME', 'justdata-mergermeter-output')
    return client.bucket(bucket_name)


def upload_json(blob_path: str, data: Any, bucket_name: Optional[str] = None) -> bool:
    """
    Upload JSON data to GCS.

    Args:
        blob_path: Path within the bucket (e.g., 'mergermeter/data_123.json')
        data: Python object to serialize as JSON
        bucket_name: Optional bucket name override

    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        bucket = get_bucket(bucket_name)
        blob = bucket.blob(blob_path)
        json_str = json.dumps(data, indent=2, default=str)
        blob.upload_from_string(json_str, content_type='application/json')
        print(f"[GCS] Uploaded {blob_path} ({len(json_str)} bytes)")
        return True
    except Exception as e:
        print(f"[GCS] Failed to upload {blob_path}: {e}")
        return False


def download_json(blob_path: str, bucket_name: Optional[str] = None) -> Optional[Any]:
    """
    Download JSON data from GCS.

    Args:
        blob_path: Path within the bucket (e.g., 'mergermeter/data_123.json')
        bucket_name: Optional bucket name override

    Returns:
        Deserialized JSON data, or None if not found or error
    """
    try:
        bucket = get_bucket(bucket_name)
        blob = bucket.blob(blob_path)
        if not blob.exists():
            print(f"[GCS] Blob not found: {blob_path}")
            return None
        content = blob.download_as_string()
        print(f"[GCS] Downloaded {blob_path} ({len(content)} bytes)")
        return json.loads(content)
    except Exception as e:
        print(f"[GCS] Failed to download {blob_path}: {e}")
        return None


def upload_file(blob_path: str, local_path: str, bucket_name: Optional[str] = None) -> bool:
    """
    Upload a local file to GCS.

    Args:
        blob_path: Destination path within the bucket
        local_path: Local file path to upload
        bucket_name: Optional bucket name override

    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        bucket = get_bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(local_path)
        print(f"[GCS] Uploaded file {local_path} -> {blob_path}")
        return True
    except Exception as e:
        print(f"[GCS] Failed to upload file {local_path}: {e}")
        return False


def download_file(blob_path: str, local_path: str, bucket_name: Optional[str] = None) -> bool:
    """
    Download a GCS blob to local file.

    Args:
        blob_path: Source path within the bucket
        local_path: Local file path to save to
        bucket_name: Optional bucket name override

    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        bucket = get_bucket(bucket_name)
        blob = bucket.blob(blob_path)
        if not blob.exists():
            print(f"[GCS] Blob not found: {blob_path}")
            return False
        blob.download_to_filename(local_path)
        print(f"[GCS] Downloaded file {blob_path} -> {local_path}")
        return True
    except Exception as e:
        print(f"[GCS] Failed to download file {blob_path}: {e}")
        return False


def file_exists(blob_path: str, bucket_name: Optional[str] = None) -> bool:
    """
    Check if a blob exists in GCS.

    Args:
        blob_path: Path within the bucket to check
        bucket_name: Optional bucket name override

    Returns:
        bool: True if blob exists, False otherwise
    """
    try:
        bucket = get_bucket(bucket_name)
        blob = bucket.blob(blob_path)
        return blob.exists()
    except Exception as e:
        print(f"[GCS] Failed to check existence of {blob_path}: {e}")
        return False


def delete_blob(blob_path: str, bucket_name: Optional[str] = None) -> bool:
    """
    Delete a blob from GCS.

    Args:
        blob_path: Path within the bucket to delete
        bucket_name: Optional bucket name override

    Returns:
        bool: True if deletion successful or blob didn't exist, False otherwise
    """
    try:
        bucket = get_bucket(bucket_name)
        blob = bucket.blob(blob_path)
        if blob.exists():
            blob.delete()
            print(f"[GCS] Deleted {blob_path}")
        return True
    except Exception as e:
        print(f"[GCS] Failed to delete {blob_path}: {e}")
        return False


def list_blobs(prefix: str, bucket_name: Optional[str] = None) -> list:
    """
    List blobs in GCS with a given prefix.

    Args:
        prefix: Prefix to filter blobs (e.g., 'mergermeter/')
        bucket_name: Optional bucket name override

    Returns:
        List of blob names matching the prefix
    """
    try:
        bucket = get_bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
    except Exception as e:
        print(f"[GCS] Failed to list blobs with prefix {prefix}: {e}")
        return []
