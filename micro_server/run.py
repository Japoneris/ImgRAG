#!/usr/bin/env python3
"""Entry point for the image embedding micro-server."""
import argparse
import os

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Image embedding micro-server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda", "gpu"],
        default=None,
        help="Device for inference (default: auto)",
    )
    args = parser.parse_args()

    if args.device:
        os.environ["DEVICE"] = args.device

    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
