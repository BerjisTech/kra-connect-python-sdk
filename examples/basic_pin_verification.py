"""
Basic PIN Verification Example

This example demonstrates how to verify a single KRA PIN number
using the KRA-Connect Python SDK.
"""

import os
from dotenv import load_dotenv

from kra_connect import KraClient, KraConnectError

# Load environment variables from .env file
load_dotenv()


def main():
    """Main example function."""
    # Initialize the client with API key from environment
    client = KraClient(api_key=os.getenv("KRA_API_KEY"))

    # PIN to verify
    pin_number = "P051234567A"

    try:
        # Verify the PIN
        print(f"Verifying PIN: {pin_number}...")
        result = client.verify_pin(pin_number)

        # Check if PIN is valid
        if result.is_valid:
            print("✓ PIN is valid!")
            print(f"  Taxpayer Name: {result.taxpayer_name}")
            print(f"  Status: {result.status}")
            print(f"  Business Type: {result.business_type}")
            print(f"  Registration Date: {result.registration_date}")
            print(f"  Email: {result.email}")
            print(f"  Phone: {result.phone_number}")
        else:
            print("✗ PIN is not valid")
            if result.error_message:
                print(f"  Error: {result.error_message}")

    except KraConnectError as e:
        print(f"Error: {e}")

    finally:
        # Close the client
        client.close()


if __name__ == "__main__":
    main()
