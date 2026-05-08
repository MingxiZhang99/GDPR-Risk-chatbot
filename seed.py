import os
from pathlib import Path
from config import COLLECTION_NAME
from vectorstore import ingest, ensure_collection, qdrant

SEED_DIR = Path(__file__).parent / "seed_data"

ARTICLE_META = {
    "art4_definitions.txt": {"topic": "gdpr", "type": "definitions", "article": "Art.4"},
    "art5_principles.txt": {"topic": "gdpr", "type": "principles", "article": "Art.5"},
    "art6_lawful_basis.txt": {"topic": "gdpr", "type": "principles", "article": "Art.6"},
    "art7_consent.txt": {"topic": "gdpr", "type": "rights", "article": "Art.7"},
    "art9_special_categories.txt": {"topic": "gdpr", "type": "principles", "article": "Art.9"},
    "art12_transparency.txt": {"topic": "gdpr", "type": "rights", "article": "Art.12"},
    "art13_information.txt": {"topic": "gdpr", "type": "rights", "article": "Art.13"},
    "art15_right_of_access.txt": {"topic": "gdpr", "type": "rights", "article": "Art.15"},
    "art16_18_21_rights.txt": {"topic": "gdpr", "type": "rights", "article": "Art.16,18,21"},
    "art17_right_to_erasure.txt": {"topic": "gdpr", "type": "rights", "article": "Art.17"},
    "art20_data_portability.txt": {"topic": "gdpr", "type": "rights", "article": "Art.20"},
    "art22_automated_decisions.txt": {"topic": "gdpr", "type": "rights", "article": "Art.22"},
    "art25_data_protection_by_design.txt": {"topic": "gdpr", "type": "principles", "article": "Art.25"},
    "art28_processor.txt": {"topic": "gdpr", "type": "obligations", "article": "Art.28"},
    "art30_records.txt": {"topic": "gdpr", "type": "obligations", "article": "Art.30"},
    "art32_security.txt": {"topic": "gdpr", "type": "security", "article": "Art.32"},
    "art33_data_breach_notification.txt": {"topic": "gdpr", "type": "security", "article": "Art.33"},
    "art34_breach_communication.txt": {"topic": "gdpr", "type": "security", "article": "Art.34"},
    "art35_dpia.txt": {"topic": "gdpr", "type": "obligations", "article": "Art.35"},
    "art37_39_dpo.txt": {"topic": "gdpr", "type": "obligations", "article": "Art.37-39"},
    "art44_49_international_transfers.txt": {"topic": "gdpr", "type": "transfers", "article": "Art.44-49"},
    "art83_fines.txt": {"topic": "gdpr", "type": "enforcement", "article": "Art.83"},
    "gdpr_ai_guidance.txt": {"topic": "gdpr", "type": "guidance", "article": "AI/ML"},
}


def collection_is_empty() -> bool:
    ensure_collection()
    info = qdrant.get_collection(COLLECTION_NAME)
    return info.points_count == 0


def load_seed_data():
    if not collection_is_empty():
        print("[seed] Knowledge base already populated, skipping.")
        return

    print("[seed] Loading GDPR seed data...")
    for filename in sorted(SEED_DIR.glob("*.txt")):
        text = filename.read_text(encoding="utf-8")
        meta = ARTICLE_META.get(filename.name, {"topic": "gdpr"})
        result = ingest(text, source=filename.name, metadata=meta)
        print(f"  ✓ {filename.name} → {result['chunks_stored']} chunks")

    print("[seed] Done.")
