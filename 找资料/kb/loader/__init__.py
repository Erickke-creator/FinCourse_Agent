"""
Knowledge Base Loader — public API surface.

Usage:
    from kb_loader import KnowledgeBase, KBQuery

    kb = KnowledgeBase()
    query = KBQuery(kb)

    banks = query.get_all_banks()
    tax_score = query.get_tax_score("A")
    info = query.get_industry_acceptance("manufacturing")

    for src in query.get_accessed_sources():
        print(f"[{src.domain}] {src.description}")
"""

try:
    from .loader import KnowledgeBase
    from .querier import KBQuery, KBSourceRecord
    from .config import KBConfig
except ImportError:
    from loader import KnowledgeBase  # type: ignore[no-redef]
    from querier import KBQuery, KBSourceRecord  # type: ignore[no-redef]
    from config import KBConfig  # type: ignore[no-redef]

__all__ = ["KnowledgeBase", "KBQuery", "KBSourceRecord", "KBConfig"]
__version__ = "1.0.0"
