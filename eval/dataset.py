"""Dataset splitting and sealed holdout management."""

import hashlib
import json
from typing import Dict, List, Tuple
from eval.generator import SyntheticPopulationGenerator
from eval.schemas import TransactionRecord


class EvaluationDataset:
    """Manages deterministic dataset generation and sealed DEV/TEST/HOLDOUT partitioning."""
    
    @staticmethod
    def partition_population(
        records: List[TransactionRecord]
    ) -> Dict[str, List[TransactionRecord]]:
        """Partitions population into DEV (60%), TEST (20%), and HOLDOUT (20%)."""
        total = len(records)
        dev_end = int(total * 0.60)
        test_end = dev_end + int(total * 0.20)
        
        return {
            "dev": records[:dev_end],
            "test": records[dev_end:test_end],
            "holdout": records[test_end:]
        }
    
    @classmethod
    def load_dataset(
        cls,
        seed: int = 42,
        n: int = 10000,
        split: str = "holdout"
    ) -> List[TransactionRecord]:
        """Generates population for the seed and returns the requested split."""
        generator = SyntheticPopulationGenerator(seed=seed)
        all_records = generator.generate_population(n)
        splits = cls.partition_population(all_records)
        
        split_key = split.lower().strip()
        if split_key not in splits:
            raise ValueError(f"Unknown split '{split}'. Must be one of: dev, test, holdout")
        
        return splits[split_key]
    
    @classmethod
    def compute_split_manifest_hash(cls, records: List[TransactionRecord]) -> str:
        """Computes a cryptographic SHA-256 manifest hash of the dataset split."""
        summary = [
            f"{r.observable.case_id}:{r.observable.payment.amount_paise}:{r.observable.payment.failure_code}"
            for r in records
        ]
        raw = "\n".join(summary)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
