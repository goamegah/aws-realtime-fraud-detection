from pathlib import Path
from typing import Optional
import mimetypes

import boto3
from botocore.config import Config as BotoConfig


def get_boto3_session(region: Optional[str] = None, profile: Optional[str] = None) -> boto3.session.Session:
    if profile:
        return boto3.session.Session(profile_name=profile, region_name=region)
    return boto3.session.Session(region_name=region)


def upload_file(
    *,
    session: boto3.session.Session,
    bucket: str,
    key: str,
    file_path: Path,
) -> None:
    s3 = session.client("s3", config=BotoConfig(retries={"max_attempts": 10, "mode": "standard"}))
    content_type, _ = mimetypes.guess_type(str(file_path))
    extra = {"ContentType": content_type} if content_type else None
    s3.upload_file(str(file_path), bucket, key, ExtraArgs=extra or {})
