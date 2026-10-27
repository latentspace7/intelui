import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter

import httpx

from app.crm_catalog import CRM_COMPONENTS, EXAMPLES


def run(kind: str, base_url: str) -> dict:
    start = perf_counter()
    spec = CRM_COMPONENTS[kind]
    question = f"{EXAMPLES[kind][0]} Use the {spec.title.lower()} component."
    try:
        response = httpx.post(f"{base_url}/api/analyses", json={"question": question}, timeout=300)
        body = response.json()
        if response.status_code != 201:
            return {
                "kind": kind,
                "passed": False,
                "status": response.status_code,
                "error": body.get("error"),
                "seconds": round(perf_counter() - start, 1),
            }
        snapshot = body["snapshot"]
        names = [
            node["component"]
            for message in snapshot["ui"]
            for node in message.get("updateComponents", {}).get("components", [])
        ]
        return {
            "kind": kind,
            "passed": spec.name in names,
            "components": names,
            "analysis_id": body["id"],
            "seconds": round(perf_counter() - start, 1),
            "snapshot": snapshot,
        }
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "kind": kind,
            "passed": False,
            "error": str(exc),
            "seconds": round(perf_counter() - start, 1),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Billable live-model checks; creates CRM conversation history."
    )
    parser.add_argument("--only", nargs="+", choices=list(EXAMPLES))
    parser.add_argument("--base-url", default="http://127.0.0.1:8018")
    parser.add_argument("--output", default="/tmp/intelui-crm-live-results.json")
    args = parser.parse_args()
    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, kind, args.base_url) for kind in (args.only or EXAMPLES)]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                json.dumps({key: value for key, value in result.items() if key != "snapshot"}),
                flush=True,
            )
    Path(args.output).write_text(json.dumps(results, indent=2))
    raise SystemExit(0 if all(item["passed"] for item in results) else 1)
