"""
Deduplicator and integrity verifier for benchmark cases.
"""
from typing import List, Dict, Tuple, Set, Any
from ..schemas.case_schema import BenchmarkCase


class Deduplicator:
    @staticmethod
    def verify_and_deduplicate(cases: List[BenchmarkCase]) -> Tuple[List[BenchmarkCase], Dict[str, Any]]:
        seen_ids: Set[str] = set()
        duplicates: List[str] = []
        unique_cases: List[BenchmarkCase] = []
        
        pair_map: Dict[str, List[BenchmarkCase]] = {}
        
        for case in cases:
            if case.test_id in seen_ids:
                duplicates.append(case.test_id)
            else:
                seen_ids.add(case.test_id)
                unique_cases.append(case)
                
            if case.contrast_pair_id:
                pair_map.setdefault(case.contrast_pair_id, []).append(case)
                
        # Validate contrast pairs
        broken_pairs = []
        for cpid, pair in pair_map.items():
            if len(pair) != 2:
                broken_pairs.append(cpid)
                
        stats = {
            "total_input": len(cases),
            "total_unique": len(unique_cases),
            "duplicates_count": len(duplicates),
            "total_contrast_pairs": len(pair_map),
            "broken_pairs_count": len(broken_pairs),
        }
        return unique_cases, stats
