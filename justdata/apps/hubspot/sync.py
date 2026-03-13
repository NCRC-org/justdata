"""
HubSpot Data Synchronization

Handles bulk data sync operations between JustData and HubSpot.
For the daily BigQuery <-> HubSpot sync, see daily_sync.py.
"""

from typing import List, Dict, Any, Optional
import asyncio
import structlog

from .client import HubSpotClient

logger = structlog.get_logger(__name__)


class HubSpotSyncManager:
    """Manager for synchronizing contact/company data with HubSpot."""

    def __init__(self, access_token: Optional[str] = None):
        self.client = HubSpotClient(access_token=access_token)

    async def sync_contacts_batch(
        self, contacts: List[Dict[str, Any]], batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Sync a batch of contacts to HubSpot (upsert by email).

        Args:
            contacts: List of contact property dicts (must include "email")
            batch_size: Number of contacts to process at once

        Returns:
            Sync results with created/updated/failed counts
        """
        logger.info(
            "Starting batch contact sync",
            total_contacts=len(contacts),
            batch_size=batch_size,
        )

        results: Dict[str, Any] = {
            "total": len(contacts),
            "created": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        for i in range(0, len(contacts), batch_size):
            batch = contacts[i : i + batch_size]
            logger.info(
                "Processing batch",
                batch_number=i // batch_size + 1,
                batch_size=len(batch),
            )

            tasks = [self._sync_single_contact(contact) for contact in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results["failed"] += 1
                    results["errors"].append(
                        {"contact": batch[idx].get("email"), "error": str(result)}
                    )
                elif result.get("created"):
                    results["created"] += 1
                else:
                    results["updated"] += 1

            if i + batch_size < len(contacts):
                await asyncio.sleep(1)

        logger.info("Batch contact sync completed", results=results)
        return results

    async def _sync_single_contact(
        self, contact_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upsert a single contact by email."""
        email = contact_data.get("email")
        if not email:
            raise ValueError("Contact email is required")

        existing = await self.client.search_contacts(
            [{"propertyName": "email", "operator": "EQ", "value": email}],
            limit=1,
        )

        if existing:
            contact_id = existing[0]["id"]
            properties = {k: v for k, v in contact_data.items() if k != "email"}
            await self.client.update_contact(contact_id, properties)
            return {"contact_id": contact_id, "created": False}
        else:
            created = await self.client.create_contact(contact_data)
            return {"contact_id": created["id"], "created": True}
