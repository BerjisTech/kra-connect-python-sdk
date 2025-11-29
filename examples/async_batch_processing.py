"""
Async Batch Processing Example

This example demonstrates how to verify multiple PINs concurrently
using the async client for improved performance.
"""

import asyncio
import os
from dotenv import load_dotenv

from kra_connect import AsyncKraClient, KraConnectError

load_dotenv()


async def verify_multiple_pins():
    """Verify multiple PINs concurrently."""
    # PINs to verify
    pins_to_verify = [
        "P051234567A",
        "P051234567B",
        "P051234567C",
        "P051234567D",
        "P051234567E",
    ]

    async with AsyncKraClient(api_key=os.getenv("KRA_API_KEY")) as client:
        print(f"Verifying {len(pins_to_verify)} PINs concurrently...")

        # Create tasks for all PINs
        tasks = [client.verify_pin(pin) for pin in pins_to_verify]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        print("\nResults:")
        print("-" * 80)

        for pin, result in zip(pins_to_verify, results):
            if isinstance(result, Exception):
                print(f"✗ {pin}: Error - {result}")
            elif result.is_valid:
                print(f"✓ {pin}: {result.taxpayer_name} ({result.status})")
            else:
                print(f"✗ {pin}: Invalid PIN")

        # Summary
        valid_count = sum(1 for r in results if not isinstance(r, Exception) and r.is_valid)
        print("-" * 80)
        print(f"Summary: {valid_count}/{len(pins_to_verify)} valid PINs")


async def batch_with_error_handling():
    """Demonstrate batch processing with proper error handling."""
    pins = ["P051234567A", "INVALID_PIN", "P051234567C"]

    async with AsyncKraClient(api_key=os.getenv("KRA_API_KEY")) as client:
        results = []

        for pin in pins:
            try:
                result = await client.verify_pin(pin)
                results.append({"pin": pin, "status": "success", "result": result})
            except KraConnectError as e:
                results.append({"pin": pin, "status": "error", "error": str(e)})

        # Display results
        print("\nBatch Results with Error Handling:")
        print("-" * 80)

        for item in results:
            if item["status"] == "success":
                result = item["result"]
                print(f"✓ {item['pin']}: {result.taxpayer_name}")
            else:
                print(f"✗ {item['pin']}: {item['error']}")


def main():
    """Run async examples."""
    print("Example 1: Concurrent PIN Verification")
    print("=" * 80)
    asyncio.run(verify_multiple_pins())

    print("\n\nExample 2: Batch with Error Handling")
    print("=" * 80)
    asyncio.run(batch_with_error_handling())


if __name__ == "__main__":
    main()
