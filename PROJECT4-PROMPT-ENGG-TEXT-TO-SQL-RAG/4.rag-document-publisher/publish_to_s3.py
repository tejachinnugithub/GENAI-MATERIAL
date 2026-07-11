import argparse
import json
import os
import sys
from pathlib import Path

import boto3

sys.path.append(str(Path(__file__).resolve().parents[1]))

from shared.rag.documents import checksum_text, parse_markdown_document


def build_manifest(doc_root: Path, bucket: str, prefix: str) -> list[dict[str, str]]:
    manifest: list[dict[str, str]] = []
    for path in sorted(doc_root.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        frontmatter, _ = parse_markdown_document(raw)
        relative_path = path.relative_to(doc_root).as_posix()
        s3_key = f"{prefix.rstrip('/')}/{relative_path}" if prefix else relative_path
        manifest.append(
            {
                "doc_id": frontmatter.get("doc_id", relative_path),
                "doc_type": frontmatter.get("doc_type", "unknown"),
                "domain": frontmatter.get("domain", "general"),
                "owner": frontmatter.get("owner", "unknown"),
                "checksum": checksum_text(raw),
                "local_path": str(path),
                "s3_uri": f"s3://{bucket}/{s3_key}",
            }
        )
    return manifest


def list_existing_markdown_keys(s3, bucket: str, prefix: str) -> set[str]:
    keys: set[str] = set()
    paginator = s3.get_paginator("list_objects_v2")
    normalized_prefix = f"{prefix.rstrip('/')}/" if prefix else ""
    for page in paginator.paginate(Bucket=bucket, Prefix=normalized_prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.endswith(".md"):
                keys.add(key)
    return keys


def delete_removed_documents(s3, bucket: str, prefix: str, local_keys: set[str]) -> list[str]:
    existing_keys = list_existing_markdown_keys(s3, bucket, prefix)
    removed_keys = sorted(existing_keys - local_keys)
    for key in removed_keys:
        s3.delete_object(Bucket=bucket, Key=key)
    return removed_keys


def publish(doc_root: str, bucket: str, prefix: str, manifest_key: str, delete_removed: bool = False) -> None:
    root = Path(doc_root)
    if not root.exists():
        raise FileNotFoundError(f"Document root does not exist: {doc_root}")

    s3 = boto3.client("s3")
    manifest = build_manifest(root, bucket, prefix)
    local_keys: set[str] = set()

    for item in manifest:
        local_path = Path(item["local_path"])
        key = item["s3_uri"].replace(f"s3://{bucket}/", "")
        local_keys.add(key)
        raw = local_path.read_text(encoding="utf-8")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=raw.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
            Metadata={
                "doc-id": item["doc_id"],
                "doc-type": item["doc_type"],
                "domain": item["domain"],
                "owner": item["owner"],
                "checksum": item["checksum"],
                "git-commit": os.environ.get("GITHUB_SHA", os.environ.get("GIT_COMMIT_SHA", "local")),
            },
        )

    removed_keys: list[str] = []
    if delete_removed:
        removed_keys = delete_removed_documents(s3, bucket, prefix, local_keys)

    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(
            {
                "documents": manifest,
                "removed_keys": removed_keys,
                "git_commit": os.environ.get("GITHUB_SHA", os.environ.get("GIT_COMMIT_SHA", "local")),
            },
            indent=2,
        ).encode("utf-8"),
        ContentType="application/json",
    )
    print(json.dumps({
        "published": len(manifest),
        "removed": len(removed_keys),
        "bucket": bucket,
        "prefix": prefix,
        "manifest_key": manifest_key,
    }))


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish reviewed RAG docs to S3.")
    parser.add_argument("--doc-root", default="rag-docs")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="business-docs")
    parser.add_argument("--manifest-key", default="manifests/latest.json")
    parser.add_argument("--delete-removed", action="store_true", help="Delete markdown files from S3 that no longer exist locally.")
    args = parser.parse_args()
    publish(args.doc_root, args.bucket, args.prefix, args.manifest_key, args.delete_removed)


if __name__ == "__main__":
    main()
