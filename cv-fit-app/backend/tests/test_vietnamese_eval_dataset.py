import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "dataset" / "vietnamese_eval"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_vietnamese_eval_dataset_has_expected_shape() -> None:
    cvs = read_jsonl(DATASET / "cvs" / "metadata.jsonl")
    jobs = read_jsonl(DATASET / "jobs" / "metadata.jsonl")
    with (DATASET / "pairs" / "evaluation_pairs.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        pairs = list(csv.DictReader(handle))

    assert len(cvs) == 60
    assert len(jobs) == 150
    assert len(pairs) == 300
    assert all(cv["synthetic"] and not cv["contains_personal_data"] for cv in cvs)
    assert all(job["source"] == "synthetic" for job in jobs)
    assert {pair["split"] for pair in pairs} == {
        "human_labelled",
        "deliberate_mismatch",
        "closely_related",
    }
    assert all((DATASET / cv["text_path"]).is_file() for cv in cvs)
    assert all((DATASET / job["text_path"]).is_file() for job in jobs)
