#!/usr/bin/env python3
"""
Deployment utility for AWS Glue artifacts.

Features:
- Build wheel
- Upload wheel, Glue job script, and Kinesis connector JAR to S3

Usage examples:
- python -m devops.deploy.cli build
- python -m devops.deploy.cli upload --bucket my-bucket --region eu-west-1
- python -m devops.deploy.cli deploy --bucket my-bucket --prefix fraudit

Reads defaults from .env: SPARK_SOLUTIONS_S3_BUCKET, SPARK_SOLUTION_NAME, AWS_REGION
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional
import urllib.request

from .config import default_config
from .s3_uploader import get_boto3_session, upload_file
from .builder import run_build, find_latest_wheel


def download_file(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def _resolve_args() -> argparse.Namespace:
    cfg = default_config()

    p = argparse.ArgumentParser(description="Deploy Glue artifacts (wheel, job script, kinesis jar) to S3")

    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--bucket", default=cfg.bucket, help="Target S3 bucket (env SPARK_SOLUTION_S3_BUCKET)")
    common.add_argument("--region", default=cfg.region, help="AWS region (env AWS_REGION)")
    common.add_argument("--profile", default=None, help="AWS profile to use (optional)")
    common.add_argument("--prefix", default=cfg.solution_prefix, help="Solution prefix for keys (env SPARK_SOLUTION_NAME)")
    common.add_argument("--no-solution-prefix", action="store_true", help="Do not prepend solution prefix to keys")

    # Paths and prefixes
    common.add_argument("--job-path", default=str(cfg.job_path), help="Local path to Glue job script")
    common.add_argument("--jar-path", default=str(cfg.jar_path), help="Local path to Kinesis connector JAR")
    common.add_argument("--dist-dir", default=str(cfg.dist_dir), help="Local dist directory for wheels")
    common.add_argument("--jobs-prefix", default=cfg.jobs_prefix, help="S3 key prefix for jobs")
    common.add_argument("--jars-prefix", default=cfg.jars_prefix, help="S3 key prefix for jars")
    common.add_argument("--wheels-prefix", default=cfg.wheels_prefix, help="S3 key prefix for wheels")

    # Optional download for jar
    common.add_argument("--jar-url", default=None, help="If provided and Kinesis connector jar-path does not exist, download from URL")

    # build subcommand
    sp_build = sub.add_parser("build", parents=[common], help="Build the wheel with python -m build")
    sp_build.add_argument("--python", default="python3", help="Python executable to use for building")

    # upload subcommand
    sp_upload = sub.add_parser("upload", parents=[common], help="Upload artifacts to S3")
    sp_upload.add_argument("--wheel", default=None, help="Explicit wheel file to upload (defaults to latest in dist)")

    # deploy subcommand (build + upload)
    sp_deploy = sub.add_parser("deploy", parents=[common], help="Build wheel then upload all artifacts")
    sp_deploy.add_argument("--python", default="python3", help="Python executable to use for building")
    sp_deploy.add_argument("--wheel", default=None, help="Explicit wheel file to upload (defaults to latest in dist)")

    return p.parse_args()


def _validate_bucket(arg: Optional[str]) -> str:
    if not arg:
        print("ERROR: S3 bucket not provided. Use --bucket or set SOLUTIONS_S3_BUCKET in .env", file=sys.stderr)
        sys.exit(2)
    return arg


def _maybe_download_jar(jar_path: Path, jar_url: Optional[str]) -> Path:
    if jar_path.exists():
        return jar_path
    if jar_url:
        print(f"Downloading Kinesis connector JAR from {jar_url} ...")
        return download_file(jar_url, jar_path)
    print(f"WARNING: JAR not found at {jar_path}. Provide --jar-url to download it or adjust --jar-path.")
    return jar_path


def _upload_all(
    *,
    bucket: str,
    prefix: Optional[str],
    jobs_prefix: str,
    jars_prefix: str,
    wheels_prefix: str,
    job_path: Path,
    jar_path: Path,
    wheel_path: Optional[Path],
    region: Optional[str],
    profile: Optional[str],
    include_solution_prefix: bool,
) -> None:
    session = get_boto3_session(region=region, profile=profile)

    # Glue job script
    job_key = jobs_prefix.rstrip("/") + "/" + job_path.name
    if include_solution_prefix and prefix:
        job_key = f"{prefix}/{job_key}"
    print(f"Uploading Glue job: {job_path} -> s3://{bucket}/{job_key}")
    upload_file(session=session, bucket=bucket, key=job_key, file_path=job_path)

    # Kinesis connector JAR
    if jar_path.exists():
        jar_key = jars_prefix.rstrip("/") + "/" + jar_path.name
        if include_solution_prefix and prefix:
            jar_key = f"{prefix}/{jar_key}"
        print(f"Uploading JAR: {jar_path} -> s3://{bucket}/{jar_key}")
        upload_file(session=session, bucket=bucket, key=jar_key, file_path=jar_path)
    else:
        print(f"WARNING: Skipping JAR upload; file not found: {jar_path}")

    # Wheel
    if wheel_path and wheel_path.exists():
        wheel_key = wheels_prefix.rstrip("/") + "/" + wheel_path.name
        if include_solution_prefix and prefix:
            wheel_key = f"{prefix}/{wheel_key}"
        print(f"Uploading wheel: {wheel_path} -> s3://{bucket}/{wheel_key}")
        upload_file(session=session, bucket=bucket, key=wheel_key, file_path=wheel_path)
    else:
        print("WARNING: Skipping wheel upload; wheel not found.")



def main() -> None:
    args = _resolve_args()

    bucket = _validate_bucket(args.bucket)
    include_solution_prefix = not args.no_solution_prefix

    # Resolve paths
    job_path = Path(args.job_path).resolve()
    jar_path = Path(args.jar_path).resolve()
    dist_dir = Path(args.dist_dir).resolve()

    # Optionally download jar
    jar_path = _maybe_download_jar(jar_path, args.jar_url)

    if args.cmd == "build":
        run_build(python_exe=args.python)
        print("Build completed.")
        return

    if args.cmd in ("upload", "deploy"):
        wheel_path: Optional[Path] = None
        if args.cmd == "deploy":
            run_build(python_exe=args.python)
        if args.wheel:
            wheel_path = Path(args.wheel).resolve()
        else:
            wheel_path = find_latest_wheel(dist_dir)
        if not wheel_path:
            print(f"WARNING: No wheel found in {dist_dir}. You may pass --wheel explicitly.")

        _upload_all(
            bucket=bucket,
            prefix=args.prefix,
            jobs_prefix=args.jobs_prefix,
            jars_prefix=args.jars_prefix,
            wheels_prefix=args.wheels_prefix,
            job_path=job_path,
            jar_path=jar_path,
            wheel_path=wheel_path,
            region=args.region,
            profile=args.profile,
            include_solution_prefix=include_solution_prefix,
        )
        print("Upload completed.")
        return


if __name__ == "__main__":
    main()
