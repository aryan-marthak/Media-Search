"""
Flickr8k Dataset Ingestion Script for Media-Search Evaluation.

Usage (run from d:/Media-Search/Metrics):
  python ingest_flickr8k.py --username YOUR_USER --password YOUR_PASS --count 500

This script:
  1. Reads captions.txt in the current directory
  2. Randomly samples --count images from the Images/ subfolder
  3. Uploads each image to Media-Search via the /upload API
  4. Builds a ground_truth_flickr8k.json mapping captions -> system image IDs
"""
import os
import sys
import random
import time
import requests
import json
import logging
import argparse
import csv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

BASE_URL = "http://localhost:8000"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_auth_token(email: str, password: str) -> str:
    """Authenticate and return the JWT token. Auto-registers if account doesn't exist."""
    # Try login first
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    if response.status_code == 200:
        logging.info("Login successful.")
        return response.json()["access_token"]

    # Login failed — try registering a new account
    logging.info("Login failed. Attempting to register a new account...")
    reg_response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "username": email.split("@")[0] + "_eval",
            "email": email,
            "password": password,
        },
    )
    if reg_response.status_code in (200, 201):
        logging.info(f"Registered new account: {email}")
        return reg_response.json()["access_token"]

    raise Exception(
        f"Could not login or register.\n"
        f"  Login response: {response.text}\n"
        f"  Register response: {reg_response.text}"
    )


def parse_captions(captions_path: str) -> dict:
    """Parse captions.txt -> {image_filename: [caption1, caption2, ...]}"""
    image_to_captions = {}
    with open(captions_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header: image,caption
        for row in reader:
            if len(row) < 2:
                continue
            img_name, caption = row[0].strip(), row[1].strip()
            if img_name not in image_to_captions:
                image_to_captions[img_name] = []
            image_to_captions[img_name].append(caption)
    return image_to_captions


def ingest_dataset(token: str, email: str, password: str, num_images: int = 500):
    images_dir = os.path.join(SCRIPT_DIR, "Images")
    captions_file = os.path.join(SCRIPT_DIR, "captions.txt")

    if not os.path.isdir(images_dir):
        logging.error(f"Images/ folder not found at {images_dir}")
        sys.exit(1)
    if not os.path.isfile(captions_file):
        logging.error(f"captions.txt not found at {captions_file}")
        sys.exit(1)

    # Parse captions
    image_to_captions = parse_captions(captions_file)
    logging.info(f"Parsed captions for {len(image_to_captions)} unique images.")

    # Filter to images that actually exist on disk
    available = [
        img for img in image_to_captions
        if os.path.isfile(os.path.join(images_dir, img))
    ]
    logging.info(f"Found {len(available)} images on disk.")

    if len(available) < num_images:
        logging.warning(
            f"Requested {num_images} but only {len(available)} available. Using all."
        )
        num_images = len(available)

    selected = random.sample(available, num_images)

    # Maps: original_filename -> system_image_id  (for ground truth)
    filename_to_id = {}
    headers = {"Authorization": f"Bearer {token}"}

    logging.info(f"Starting upload of {num_images} images...")
    success = 0
    failed = 0
    start_time = time.time()

    for i, img_name in enumerate(selected, 1):
        img_path = os.path.join(images_dir, img_name)
        elapsed = time.time() - start_time
        rate = success / elapsed if elapsed > 0 else 0
        eta = (num_images - i) / rate if rate > 0 else 0

        logging.info(
            f"[{i}/{num_images}] Uploading {img_name}  "
            f"({success} ok, {failed} fail, ETA {eta:.0f}s)"
        )

        try:
            with open(img_path, "rb") as f:
                files = {"file": (img_name, f, "image/jpeg")}
                resp = requests.post(
                    f"{BASE_URL}/upload",
                    files=files,
                    headers=headers,
                    timeout=180,
                )

            # Token expired — re-login and retry this image
            if resp.status_code == 401:
                logging.warning("Token expired, re-authenticating...")
                token = get_auth_token(email, password)
                headers = {"Authorization": f"Bearer {token}"}
                with open(img_path, "rb") as f:
                    files = {"file": (img_name, f, "image/jpeg")}
                    resp = requests.post(
                        f"{BASE_URL}/upload",
                        files=files,
                        headers=headers,
                        timeout=180,
                    )

            if resp.status_code == 200:
                system_id = resp.json()["image_id"]
                filename_to_id[img_name] = system_id
                success += 1
            else:
                logging.error(f"  Upload failed ({resp.status_code}): {resp.text[:200]}")
                failed += 1
        except Exception as e:
            logging.error(f"  Exception uploading {img_name}: {e}")
            failed += 1

    total_time = time.time() - start_time
    logging.info(
        f"Upload complete: {success} succeeded, {failed} failed "
        f"in {total_time:.1f}s ({total_time/60:.1f} min)"
    )

    # Build ground truth: caption -> [list of system image IDs]
    ground_truth = {}
    for img_name, system_id in filename_to_id.items():
        for caption in image_to_captions[img_name]:
            if caption not in ground_truth:
                ground_truth[caption] = []
            ground_truth[caption].append(system_id)

    # Save ground truth
    gt_path = os.path.join(SCRIPT_DIR, "ground_truth_flickr8k.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    # Also save the filename -> id mapping (useful for debugging)
    map_path = os.path.join(SCRIPT_DIR, "filename_to_id.json")
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(filename_to_id, f, indent=2)

    logging.info(f"Ground truth saved to: {gt_path}")
    logging.info(f"Filename mapping saved to: {map_path}")
    logging.info(f"Total ground-truth queries: {len(ground_truth)}")
    logging.info("")
    logging.info("Next step: run evaluate_metrics.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest Flickr8k images into Media-Search"
    )
    parser.add_argument("--email", required=True, help="Your Media-Search login email")
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--count", type=int, default=500,
        help="Number of images to randomly sample (default: 500)",
    )
    args = parser.parse_args()

    token = get_auth_token(args.email, args.password)
    ingest_dataset(token, args.email, args.password, num_images=args.count)
