import json
import yaml
from typing import Any
from luna_shared.ir.scoring import combine_score, ScoringConfig

def calculate_mrr(golden_set: list[dict], search_service: Any) -> float:
    """
    Calculates Mean Reciprocal Rank (MRR) for a set of queries.
    golden_set: list of {"query": str, "expected_doc_id": str}
    """
    sum_rr = 0.0
    for item in golden_set:
        query = item["query"]
        expected_id = item["expected_doc_id"]

        # Perform search
        results = await search_service.search(query, page=1, per_page=100)

        # Find rank of expected_id
        rank = 0
        for i, res in enumerate(results["results"], start=1):
            if res["id"] == expected_id:
                rank = i
                break

        if rank > 0:
            sum_rr += 1.0 / rank

    return sum_rr / len(golden_set)

async def tune_weights(golden_set_path: str, config_path: str, search_service: Any):
    with open(golden_set_path, "r") as f:
        golden_set = json.load(f)

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    # Simple grid search or random sampling could be implemented here
    # For MVP, we just report current MRR
    mrr = await calculate_mrr(golden_set, search_service)
    print(f"Current MRR: {mrr:.4f}")
    return mrr
