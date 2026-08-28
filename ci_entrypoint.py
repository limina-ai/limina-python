#!/usr/bin/env python
# coding: utf-8

import os
import sys
import json
import urllib.request
import urllib.error
from limina import LiminaMonitor

def get_env_bool(key: str, default: bool = True) -> bool:
    val = os.getenv(key, str(default)).strip().lower()
    return val in ["true", "1", "yes", "y"]

def post_or_update_pr_comment(token: str, repo: str, pr_number: int, markdown_body: str):
    """Post or update regression comment Limina on Pull Request."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Limina-CI-Gate"
    }
    
    comments_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    comment_tag = "<!-- limina-regression-report-marker -->"
    full_body = f"{comment_tag}\n{markdown_body}"

    try:
        req = urllib.request.Request(comments_url, headers=headers, method="GET")
        with urllib.request.urlopen(req) as resp:
            comments = json.loads(resp.read().decode("utf-8"))

        existing_comment_id = None
        for c in comments:
            if comment_tag in c.get("body", ""):
                existing_comment_id = c["id"]
                break

        if existing_comment_id:
            update_url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_comment_id}"
            payload = json.dumps({"body": full_body}).encode("utf-8")
            update_req = urllib.request.Request(update_url, data=payload, headers=headers, method="PATCH")
            with urllib.request.urlopen(update_req):
                print(f"[limina] Updated existing PR comment (ID: {existing_comment_id}).")
        else:
            payload = json.dumps({"body": full_body}).encode("utf-8")
            create_req = urllib.request.Request(comments_url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(create_req):
                print(f"[limina] Created new regression report comment on PR #{pr_number}.")

    except Exception as e:
        print(f"[limina] Notice: Could not post PR comment: {e}")

def main():
    api_key = os.getenv("LIMINA_API_KEY")
    baseline_path = os.getenv("INPUT_BASELINE")
    candidate_path = os.getenv("INPUT_CANDIDATE")
    fail_on_regression = get_env_bool("INPUT_FAIL_ON_REGRESSION", True)
    comment_on_pr = get_env_bool("INPUT_COMMENT_ON_PR", True)
    github_token = os.getenv("INPUT_GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    event_path = os.getenv("GITHUB_EVENT_PATH")

    if not api_key:
        print("[limina] [ERROR] Missing LIMINA_API_KEY. Set it in GitHub Repository Secrets.")
        sys.exit(1)

    if not baseline_path or not os.path.exists(baseline_path):
        print(f"[limina] [ERROR] Baseline dataset file not found: [{baseline_path}]")
        sys.exit(1)

    if not candidate_path or not os.path.exists(candidate_path):
        print(f"[limina] [ERROR] Candidate dataset file not found: [{candidate_path}]")
        sys.exit(1)

    print(f"[limina] Initializing regression comparison...")
    print(f"[limina] Baseline  : {baseline_path}")
    print(f"[limina] Candidate : {candidate_path}")

    monitor = LiminaMonitor(api_key=api_key)
    result = monitor.compare(
        baseline_logs=baseline_path,
        candidate_logs=candidate_path,
        fail_on_regression=False
    )

    if not result or result.get("status") == "ERROR":
        print(f"[limina] [ERROR] Evaluation engine failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    diff = result.get("regression_analysis", {})
    ci_status = diff.get("ci_gate_status", "UNKNOWN")
    verdict = diff.get("verdict", "UNKNOWN")
    pr_markdown = diff.get("github_pr_markdown", "")
    new_regressions = diff.get("breakdown", {}).get("new_regressions_count", 0)

    if comment_on_pr and github_token and repo and event_path and os.path.exists(event_path):
        try:
            with open(event_path, "r", encoding="utf-8") as f:
                event_data = json.load(f)
            pr_number = event_data.get("pull_request", {}).get("number")
            if pr_number:
                post_or_update_pr_comment(github_token, repo, pr_number, pr_markdown)
        except Exception as err:
            print(f"[limina] PR comment resolution notice: {err}")

    # Gating logic
    if fail_on_regression and ci_status == "BLOCKED":
        print(f"\n[limina] [BLOCKED] CI Gate Failed: {new_regressions} new regression(s) detected.")
        print(f"[limina] Review the detailed diff and apply prompt patches before merging.")
        sys.exit(1)

    print(f"\n[limina] [PASSED] CI Gate Passed ({verdict}). Safe to merge.")
    sys.exit(0)

if __name__ == "__main__":
    main()