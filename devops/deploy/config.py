import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from repository root if present
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT_DIR / ".env")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


@dataclass
class DeployConfig:
    # AWS / S3
    bucket: str
    region: Optional[str]
    profile: Optional[str]
    solution_prefix: Optional[str]

    # Artifacts (local)
    job_path: Path
    jar_path: Path
    dist_dir: Path

    # S3 prefixes (remote)
    jobs_prefix: str = "spark-jobs/"
    jars_prefix: str = "jars/"
    wheels_prefix: str = "wheel/"

    # Behavior
    include_solution_prefix: bool = True

    def prefix_key(self, key: str) -> str:
        if self.include_solution_prefix and self.solution_prefix:
            return f"{self.solution_prefix.rstrip('/')}/{key.lstrip('/')}"
        return key


def default_config() -> DeployConfig:
    return DeployConfig(
        bucket=_env("SPARK_SOLUTION_S3_BUCKET", ""),
        region=_env("AWS_REGION"),
        profile=None,
        solution_prefix=_env("SPARK_SOLUTION_NAME", ""),
        job_path=(ROOT_DIR / "src" / "fraudit" / "glue_job.py"),
        jar_path=(ROOT_DIR / "src" / "resources" / "spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar"),
        dist_dir=(ROOT_DIR / "dist"),
    )
