"""
Deduplicator and integrity verifier for benchmark cases.
"""
from typing import List, Dict, Tuple, Set, Any
from ..schemas.case_schema import BenchmarkCase


class Deduplicator:
    @staticmethod
    def verify_and_deduplicate(cases: List[BenchmarkCase]) -> Tuple[List[BenchmarkCase], Dict[str, Any]]:
        seen_ids: Set[str] = set()
        seen_prompts: Set[Tuple[str, str, str]] = set()
        duplicates: List[str] = []
        prompt_duplicates: List[str] = []
        unique_cases: List[BenchmarkCase] = []
        
        pair_map: Dict[str, List[BenchmarkCase]] = {}
        
        for case in cases:
            if case.test_id in seen_ids:
                duplicates.append(case.test_id)
            else:
                seen_ids.add(case.test_id)
                unique_cases.append(case)
                
            prompt_key = (case.actor_username, case.requested_action, case.target_resource)
            if prompt_key in seen_prompts:
                prompt_duplicates.append(case.test_id)
            else:
                seen_prompts.add(prompt_key)
                
            if case.contrast_pair_id:
                pair_map.setdefault(case.contrast_pair_id, []).append(case)
                
        # Validate contrast pairs
        broken_pairs = []
        non_reciprocal_pairs = []
        for cpid, pair in pair_map.items():
            if len(pair) != 2:
                broken_pairs.append(cpid)
            else:
                decisions = {pair[0].expected_decision, pair[1].expected_decision}
                if decisions != {"ALLOW", "BLOCK"}:
                    non_reciprocal_pairs.append(cpid)
                
        stats = {
            "total_input": len(cases),
            "total_unique": len(unique_cases),
            "duplicates_count": len(duplicates),
            "prompt_duplicates_count": len(prompt_duplicates),
            "total_contrast_pairs": len(pair_map),
            "broken_pairs_count": len(broken_pairs),
            "non_reciprocal_pairs_count": len(non_reciprocal_pairs),
        }
        return unique_cases, stats
