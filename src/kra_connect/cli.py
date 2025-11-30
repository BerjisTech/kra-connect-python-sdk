"""
Simple command-line interface for the KRA-Connect Python SDK.

Provides quick access to common verification workflows without having
to write custom scripts. The CLI reads the API key from the --api-key
flag or the KRA_API_KEY environment variable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Dict

from kra_connect.client import KraClient
from kra_connect.config import KraConfig
from kra_connect.exceptions import KraConnectError


def _load_client(args: argparse.Namespace) -> KraClient:
    """
    Create a KraClient from CLI arguments/environment variables.

    Priority order for API key: flag -> env var. Exits with code 2 if missing.
    """
    api_key = args.api_key or os.getenv("KRA_API_KEY")
    if not api_key:
        print(
            "Error: API key is required. Provide --api-key or set KRA_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(2)

    config_kwargs: Dict[str, Any] = {
        "api_key": api_key,
    }

    if args.base_url:
        config_kwargs["base_url"] = args.base_url
    if args.timeout:
        config_kwargs["timeout"] = args.timeout

    config = KraConfig(**config_kwargs)
    return KraClient(config=config)


def _print_json(data: Any) -> None:
    """Pretty-print dictionaries or pydantic models as JSON."""
    if hasattr(data, "model_dump"):
        payload = data.model_dump()
    elif hasattr(data, "__dict__"):
        payload = data.__dict__
    else:
        payload = data

    print(json.dumps(payload, default=str, indent=2))


def _handle_client_call(
    args: argparse.Namespace,
    handler: Callable[[KraClient, argparse.Namespace], Any],
) -> None:
    """Execute a handler with error handling and resource cleanup."""
    client = _load_client(args)
    try:
        result = handler(client, args)
        if result is not None:
            _print_json(result)
    except KraConnectError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


def _cmd_verify_pin(client: KraClient, args: argparse.Namespace) -> Any:
    return client.verify_pin(args.pin)


def _cmd_verify_tcc(client: KraClient, args: argparse.Namespace) -> Any:
    return client.verify_tcc(args.tcc)


def _cmd_validate_eslip(client: KraClient, args: argparse.Namespace) -> Any:
    return client.validate_eslip(args.slip)


def _cmd_file_nil_return(client: KraClient, args: argparse.Namespace) -> Any:
    return client.file_nil_return(args.pin, args.period, args.obligation)


def _cmd_taxpayer_details(client: KraClient, args: argparse.Namespace) -> Any:
    return client.get_taxpayer_details(args.pin)


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        prog="kra",
        description="CLI for Kenya Revenue Authority GavaConnect integrations.",
    )
    parser.add_argument(
        "--api-key",
        help="API key for KRA GavaConnect (falls back to KRA_API_KEY env var).",
    )
    parser.add_argument(
        "--base-url",
        help="Override the default API base URL (https://api.kra.go.ke/gavaconnect/v1).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="Request timeout in seconds (default: 30).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_pin = subparsers.add_parser("verify-pin", help="Verify a KRA PIN number.")
    verify_pin.add_argument("pin", help="PIN to verify (e.g., P051234567A).")
    verify_pin.set_defaults(func=_cmd_verify_pin)

    verify_tcc = subparsers.add_parser(
        "verify-tcc",
        help="Verify a Tax Compliance Certificate number.",
    )
    verify_tcc.add_argument("tcc", help="TCC number (e.g., TCC123456).")
    verify_tcc.set_defaults(func=_cmd_verify_tcc)

    eslip = subparsers.add_parser(
        "validate-eslip",
        help="Validate an electronic slip reference.",
    )
    eslip.add_argument("slip", help="E-slip number to validate.")
    eslip.set_defaults(func=_cmd_validate_eslip)

    nil_return = subparsers.add_parser(
        "file-nil-return",
        help="File a NIL return for a PIN/obligation/period.",
    )
    nil_return.add_argument("pin", help="Taxpayer PIN.")
    nil_return.add_argument("obligation", help="Obligation identifier (e.g., OBL123456).")
    nil_return.add_argument("period", help="Tax period in YYYYMM format.")
    nil_return.set_defaults(func=_cmd_file_nil_return)

    taxpayer = subparsers.add_parser(
        "taxpayer-details",
        help="Fetch taxpayer details for a PIN.",
    )
    taxpayer.add_argument("pin", help="Taxpayer PIN.")
    taxpayer.set_defaults(func=_cmd_taxpayer_details)

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the console script."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        sys.exit(2)
    _handle_client_call(args, handler)


if __name__ == "__main__":
    main()
