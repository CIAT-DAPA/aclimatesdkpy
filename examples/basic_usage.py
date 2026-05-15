import asyncio
import os

from aclimate_sdk import AClimateClient, ContextBuilder


async def main() -> None:
    async with AClimateClient(
        client_id=os.environ["ACLIMATE_CLIENT_ID"],
        client_secret=os.environ["ACLIMATE_CLIENT_SECRET"],
    ) as client:
        countries = await client.get_countries_by_name("Colombia")
        print(ContextBuilder().countries_summary(countries))


if __name__ == "__main__":
    asyncio.run(main())
