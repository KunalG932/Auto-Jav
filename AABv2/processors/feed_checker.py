import logging
from typing import List, Dict, Any, Optional
from ..services.feed import fetch_jav, get_title, sha1
from ..db import get_last_hash, set_last_hash, get_file_by_hash

LOG = logging.getLogger("AABv2")

def check_for_new_items() -> Optional[List[Dict[str, Any]]]:
    try:
        results = fetch_jav()
        if not results:
            LOG.info("No results from feed")
            return None

        last_hash = get_last_hash()
        LOG.info(f"Current stored last_hash: {last_hash}")

        new_items: List[Dict[str, Any]] = []
        first_hash: Optional[str] = None

        for idx, item in enumerate(results):
            title = get_title(item) or ""
            current_hash = sha1(title)

            if idx == 0:
                first_hash = current_hash

            if last_hash and current_hash == last_hash:
                break

            try:
                if get_file_by_hash(current_hash):
                    LOG.info(f"Skipping already-uploaded item by hash: {title} -> {current_hash}")
                    continue

                try:
                    from ..db import files as files_collection
                    if title and files_collection.count_documents({"name": title}, limit=1) > 0:
                        LOG.info(f"Skipping already-uploaded item by name: {title}")
                        continue
                except Exception:
                    pass

            except Exception:
                LOG.warning(f"DB lookup failed while checking item '{title}'; will include it")

            new_items.append(item)

        try:
            LOG.debug(f"Feed returned {len(results)} items. New items count (before reverse): {len(new_items)}")
            if results:
                top_preview = []
                for i, it in enumerate(results[:5]):
                    t = get_title(it) or '<no-title>'
                    top_preview.append(f"{i}:{t} -> {sha1(get_title(it) or '')}")
                LOG.info("Top feed preview: " + " | ".join(top_preview))
        except Exception:
            pass

        if first_hash:
            if last_hash is not None:
                LOG.info(f"Setting last_hash to newest item: {first_hash}")
                set_last_hash(first_hash)
            else:
                LOG.info(f"Not setting last_hash on first run; newest item would be: {first_hash}")

        new_items.reverse()
        LOG.info(f"Found {len(new_items)} new items")
        return new_items if new_items else None

    except Exception as e:
        LOG.error(f"Error checking for new items: {e}")
        return None
