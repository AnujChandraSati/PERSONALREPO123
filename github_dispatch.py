import itertools
import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

# GITHUB_TARGETS_JSON env var should look like:
# [{"owner": "account1", "repo": "reddit-worker", "token": "ghp_..."},
#  {"owner": "account2", "repo": "reddit-worker", "token": "ghp_..."}]
_raw_targets = os.environ.get("GITHUB_TARGETS_JSON", "[]")
try:
    GITHUB_TARGETS = json.loads(_raw_targets)
except Exception:
    logger.error("GITHUB_TARGETS_JSON is not valid JSON -- no workers configured.")
    GITHUB_TARGETS = []

_target_cycle = itertools.cycle(GITHUB_TARGETS) if GITHUB_TARGETS else None


def dispatch_to_github(url, chat_id, message_id):
    """
    Fires a repository_dispatch event to one of the configured GitHub worker
    repos, round-robin. Falls back to the next target if one fails, trying
    each configured target at most once per call.
    Returns True if dispatch succeeded, False otherwise.
    """
    if not GITHUB_TARGETS:
        logger.error("No GitHub targets configured (GITHUB_TARGETS_JSON is empty).")
        return False

    payload = {
        "event_type": "process_url",
        "client_payload": {
            "url": url,
            "chat_id": str(chat_id),
            "message_id": str(message_id) if message_id else "",
        },
    }

    attempts = 0
    while attempts < len(GITHUB_TARGETS):
        target = next(_target_cycle)
        attempts += 1

        api_url = f"https://api.github.com/repos/{target['owner']}/{target['repo']}/dispatches"
        headers = {
            "Authorization": f"token {target['token']}",
            "Accept": "application/vnd.github+json",
        }

        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=15)
        except Exception as e:
            logger.warning("Dispatch to %s/%s failed: %s", target["owner"], target["repo"], e)
            continue

        if resp.status_code == 204:
            logger.info("Dispatched to %s/%s", target["owner"], target["repo"])
            return True

        logger.warning(
            "Dispatch to %s/%s got status %s: %s",
            target["owner"], target["repo"], resp.status_code, resp.text[:300],
        )

    logger.error("All GitHub targets failed for url=%s", url)
    return Falsegithub_dispatch.py
