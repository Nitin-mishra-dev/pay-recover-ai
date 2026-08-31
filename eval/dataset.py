"""Dataset splitting and sealed holdout management."""

import hashlib
import json
from typing import Dict, List, Tuple
from eval.generator import SyntheticPopulationGenerator
from eval.schemas import TransactionRecord, WorldVersion


class EvaluationDataset:
    """Manages deterministic dataset generation and sealed DEV/TEST/HOLDOUT partitioning.
    
    Standard Population Model:
        A population of N cases per seed (default N=10,000) is partitioned deterministically into:
        - DEV:     60% (6,000 cases) - Model training and exploratory prompt tuning
        - TEST:    20% (2,000 cases) - Validation and threshold calibration
        - HOLDOUT: 20% (2,000 cases) - Sealed out-of-sample economic benchmark
        
        When running a 5-seed benchmark on the HOLDOUT split:
        5 seeds x 2,000 cases/seed = 10,000 total evaluated observations.
    """
    
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
        split: str = "holdout",
        world_version: WorldVersion = WorldVersion.V1_STANDARD
    ) -> List[TransactionRecord]:
        """Generates population for the seed (size n) and returns the requested split (DEV 60%, TEST 20%, HOLDOUT 20%)."""
        generator = SyntheticPopulationGenerator(seed=seed, world_version=world_version)
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
