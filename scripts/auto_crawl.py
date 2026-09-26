import asyncio
import argparse
import sys
from datetime import datetime
import httpx

# Configuration (provide the API key via the LUNA_API_KEY environment variable)
import os

API_URL = os.getenv("LUNA_API_URL", "http://localhost:8000")
API_KEY = os.getenv("LUNA_API_KEY", "")

async def auto_crawl(seeds: list[str], job_name: str = "Auto Crawl"):
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create the Crawl Job
        print(f"🚀 Creating crawl job: {job_name}...")
        payload = {
            "name": job_name,
            "seed_urls": seeds,
            "allowed_domains": [], # Allow all for automation
            "max_depth": 3,
            "max_pages": 100
        }

        try:
            resp = await client.post(f"{API_URL}/api/v1/admin/crawl/jobs", json=payload, headers=headers)
            resp.raise_for_status()
            job = resp.json()
            job_id = job["id"]
            print(f"✅ Job created successfully. ID: {job_id}")
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to create job: {e.response.text}")
            return

        # 2. Run the Job
        print(f"⚙️ Starting crawl for {job_id}...")
        try:
            run_resp = await client.patch(
                f"{API_URL}/api/v1/admin/crawl/jobs/{job_id}",
                json={"action": "resume"},
                headers=headers
            )
            run_resp.raise_for_status()
            print("✅ Crawl started!")
        except httpx.HTTPStatusError as e:
            print(f"❌ Failed to start job: {e.response.text}")
            return

        # 3. Monitor Progress
        print("⏳ Monitoring progress (Ctrl+C to stop monitoring)...")
        try:
            while True:
                stats_resp = await client.get(
                    f"{API_URL}/api/v1/admin/crawl/queue/stats?job_id={job_id}",
                    headers=headers
                )
                stats_resp.raise_for_status()
                stats = stats_resp.json()

                # In the demo/local setup, we check if the job is completed via the job endpoint
                job_resp = await client.get(f"{API_URL}/api/v1/admin/crawl/jobs/{job_id}", headers=headers)
                job_resp.raise_for_status()
                current_job = job_resp.json()

                status = current_job["status"]
                pages = current_job["pages_crawled"]

                print(f"   Status: {status} | Pages Crawled: {pages}", end="\r")

                if status in ["completed", "failed", "cancelled"]:
                    print(f"\n\n🏁 Crawl finished with status: {status}")
                    break

                await asyncio.sleep(2)
        except KeyboardInterrupt:
            print("\nStopped monitoring. Crawl is still running in background.")
        except Exception as e:
            print(f"\n❌ Error monitoring progress: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Luna Auto-Crawler")
    parser.add_argument("--seeds", type=str, required=True, help="Comma-separated list of seed URLs")
    parser.add_argument("--name", type=str, default="Auto Crawl", help="Name of the crawl job")

    args = parser.parse_args()
    seed_list = [s.strip() for s in args.seeds.split(",")]

    try:
        asyncio.run(auto_crawl(seed_list, args.name))
    except KeyboardInterrupt:
        pass
