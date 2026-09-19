"""Command-line entrypoint for demo data seeding."""

import asyncio
import json

from app.seed.demo import seed_demo_data


async def main() -> None:
    result = await seed_demo_data()
    print(
        json.dumps(
            {
                "organization_id": str(result.organization_id),
                "total_entities": result.total_entities,
                "counts": result.counts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
