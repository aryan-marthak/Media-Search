"""
Search Quality Evaluation Script for Media-Search.

Usage (run from d:\Media-Search\Metrics):
  python evaluate_metrics.py --username YOUR_USER --password YOUR_PASS --mode standard
  python evaluate_metrics.py --username YOUR_USER --password YOUR_PASS --mode deep

Modes:
  standard  -> /search  (Mode 1: CLIP, or Mode 2: CLIP + re-ranking depending on backend config)
  deep      -> /deep-search  (Mode 3: Hybrid BM25 + CLIP)

Outputs Precision@5, Recall@20, mAP, and Query Success Rate.
"""
import os
import sys
import random
import time
import requests
import json
import logging
import argparse
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

BASE_URL = "http://localhost:8000"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_auth_token(email: str, password: str) -> str:
    """Authenticate and return the JWT token."""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    if resp.status_code != 200:
        raise Exception(f"Login failed: {resp.text}")
    return resp.json()["access_token"]


def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Precision@k: fraction of top-k results that are relevant."""
    if k == 0:
        return 0.0
    top_k = retrieved[:k]
    hits = len(set(top_k) & set(relevant))
    return hits / k


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Recall@k: fraction of relevant items found in top-k."""
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = len(set(top_k) & set(relevant))
    return hits / len(relevant)


def average_precision(retrieved: List[str], relevant: List[str]) -> float:
    """Average Precision for a single query."""
    if not relevant:
        return 0.0
    rel_count = 0
    prec_sum = 0.0
    for i, img_id in enumerate(retrieved):
        if img_id in relevant:
            rel_count += 1
            prec_sum += rel_count / (i + 1)
    if rel_count == 0:
        return 0.0
    return prec_sum / len(relevant)


def run_evaluation(
    token: str,
    ground_truth: Dict[str, List[str]],
    deep_search: bool = False,
    max_queries: int = 0,
):
    """Run queries and compute aggregated retrieval metrics."""
    headers = {"Authorization": f"Bearer {token}"}
    endpoint = (
        f"{BASE_URL}/deep-search" if deep_search
        else f"{BASE_URL}/search"
    )
    mode_label = "Deep Hybrid (BM25+CLIP)" if deep_search else "Standard (CLIP)"

    # Optionally sample a subset of queries
    queries = list(ground_truth.items())
    if max_queries > 0 and max_queries < len(queries):
        queries = random.sample(queries, max_queries)

    total = len(queries)
    p5_sum = 0.0
    r20_sum = 0.0
    ap_sum = 0.0
    successes = 0
    evaluated = 0
    errors = 0

    logging.info(f"{'='*60}")
    logging.info(f"Mode: {mode_label}")
    logging.info(f"Evaluating {total} queries...")
    logging.info(f"{'='*60}")

    start = time.time()

    for i, (query, expected_ids) in enumerate(queries, 1):
        if not expected_ids:
            continue

        payload = {"query": query, "top_k": 30}
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=60)
        except Exception as e:
            logging.error(f"  [{i}] Request error for '{query[:50]}': {e}")
            errors += 1
            continue

        if resp.status_code != 200:
            logging.error(f"  [{i}] HTTP {resp.status_code} for '{query[:50]}'")
            errors += 1
            continue

        results = resp.json().get("results", [])
        retrieved_ids = [str(r["image_id"]) for r in results]

        p5 = precision_at_k(retrieved_ids, expected_ids, k=5)
        r20 = recall_at_k(retrieved_ids, expected_ids, k=20)
        ap = average_precision(retrieved_ids, expected_ids)

        # Success = at least 1 relevant in top-3
        if set(retrieved_ids[:3]) & set(expected_ids):
            successes += 1

        p5_sum += p5
        r20_sum += r20
        ap_sum += ap
        evaluated += 1

        if i % 50 == 0 or i == total:
            elapsed = time.time() - start
            logging.info(
                f"  Progress: {i}/{total} queries  "
                f"({elapsed:.0f}s elapsed, {errors} errors)"
            )

    if evaluated == 0:
        logging.error("No queries were successfully evaluated.")
        return

    # Compute aggregated metrics
    avg_p5 = p5_sum / evaluated
    avg_r20 = r20_sum / evaluated
    mAP = ap_sum / evaluated
    success_rate = (successes / evaluated) * 100

    elapsed = time.time() - start

    logging.info("")
    logging.info(f"{'='*60}")
    logging.info(f"  RESULTS — {mode_label}")
    logging.info(f"{'='*60}")
    logging.info(f"  Queries evaluated : {evaluated}")
    logging.info(f"  Errors            : {errors}")
    logging.info(f"  Time              : {elapsed:.1f}s")
    logging.info(f"{'─'*60}")
    logging.info(f"  Precision@5       : {avg_p5:.4f}")
    logging.info(f"  Recall@20         : {avg_r20:.4f}")
    logging.info(f"  mAP               : {mAP:.4f}")
    logging.info(f"  Query Success Rate: {success_rate:.1f}%")
    logging.info(f"{'='*60}")

    # Save results to JSON for easy copy-paste into report
    results_file = os.path.join(
        SCRIPT_DIR,
        f"results_{'deep' if deep_search else 'standard'}.json"
    )
    results_data = {
        "mode": mode_label,
        "queries_evaluated": evaluated,
        "errors": errors,
        "precision_at_5": round(avg_p5, 4),
        "recall_at_20": round(avg_r20, 4),
        "mAP": round(mAP, 4),
        "query_success_rate_pct": round(success_rate, 1),
    }
    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2)
    logging.info(f"Results saved to: {results_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate Media-Search retrieval quality"
    )
    parser.add_argument("--email", required=True, help="Your Media-Search login email")
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--mode", required=True, choices=["standard", "deep"],
        help="standard = /search, deep = /deep-search",
    )
    parser.add_argument(
        "--ground-truth",
        default=os.path.join(SCRIPT_DIR, "ground_truth_flickr8k.json"),
        help="Path to ground truth JSON (default: ground_truth_flickr8k.json)",
    )
    parser.add_argument(
        "--max-queries", type=int, default=0,
        help="Limit number of queries to evaluate (0 = all)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.ground_truth):
        logging.error(f"Ground truth file not found: {args.ground_truth}")
        logging.error("Run ingest_flickr8k.py first to generate it.")
        sys.exit(1)

    with open(args.ground_truth, "r") as f:
        gt_data = json.load(f)

    token = get_auth_token(args.email, args.password)
    run_evaluation(
        token, gt_data,
        deep_search=(args.mode == "deep"),
        max_queries=args.max_queries,
    )
