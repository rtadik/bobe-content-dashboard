#!/usr/bin/env python3
"""
Multi-Client Configuration Loader

Central module for loading client-specific configuration. All scripts import
this to get brand assets, keywords, tone, output paths, etc. for the active client.

Active client is determined by:
1. --client CLI flag (highest priority)
2. .active-client file in workspace root
3. Falls back to "bobe" if neither exists

Usage:
    from client_config import load_config, get_brand_dir, get_output_dir

    config = load_config()                    # loads active client
    config = load_config(client_id="bobe")    # loads specific client
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CLIENTS_DIR = PROJECT_ROOT / "clients"
ACTIVE_CLIENT_FILE = PROJECT_ROOT / ".active-client"
DEFAULT_CLIENT = "bobe"


def get_active_client() -> str:
    """Read the active client ID from .active-client file, or return default."""
    if ACTIVE_CLIENT_FILE.exists():
        client_id = ACTIVE_CLIENT_FILE.read_text().strip()
        if client_id and (CLIENTS_DIR / client_id).is_dir():
            return client_id
    return DEFAULT_CLIENT


def list_clients() -> list:
    """List all available client IDs (directories under clients/, excluding _template)."""
    if not CLIENTS_DIR.exists():
        return []
    return sorted([
        d.name for d in CLIENTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "config.json").exists()
    ])


def load_config(client_id: str = None) -> dict:
    """Load and return the full config dict for the specified (or active) client."""
    if client_id is None:
        client_id = get_active_client()

    config_path = CLIENTS_DIR / client_id / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Client config not found: {config_path}\n"
            f"Available clients: {', '.join(list_clients()) or 'none'}\n"
            f"Run /onboard-client to create a new client."
        )

    with open(config_path) as f:
        config = json.load(f)

    # Ensure client_id matches directory name
    config["client_id"] = client_id
    return config


def get_client_dir(client_id: str = None) -> Path:
    """Return the root directory for the specified (or active) client."""
    if client_id is None:
        client_id = get_active_client()
    return CLIENTS_DIR / client_id


def get_brand_dir(client_id: str = None) -> Path:
    """Return the brand assets directory for the specified (or active) client."""
    return get_client_dir(client_id) / "brand"


def get_output_dir(client_id: str = None) -> Path:
    """Return the output directory for the specified (or active) client."""
    if client_id is None:
        client_id = get_active_client()
    return PROJECT_ROOT / "outputs" / "content" / client_id


def get_reference_images(client_id: str = None) -> list:
    """Return list of Paths to reference images for the specified (or active) client."""
    config = load_config(client_id)
    brand_dir = get_brand_dir(config["client_id"])
    ref_paths = config.get("brand", {}).get("reference_images", [])
    return [brand_dir.parent / p for p in ref_paths]


def get_keywords(client_id: str = None) -> list:
    """Return the keyword list for the specified (or active) client."""
    config = load_config(client_id)
    return config.get("scraping", {}).get("keywords", [])


def get_negative_keywords(client_id: str = None) -> list:
    """Return the negative keyword list for the specified (or active) client."""
    config = load_config(client_id)
    return config.get("scraping", {}).get("negative_keywords", [])


def get_subreddits(client_id: str = None) -> list:
    """Return the subreddit list for the specified (or active) client."""
    config = load_config(client_id)
    return config.get("scraping", {}).get("subreddits", [])


def get_content_guidelines_path(client_id: str = None) -> Path:
    """Return the path to the client's content guidelines file."""
    return get_client_dir(client_id) / "content-guidelines.md"


def get_keywords_path(client_id: str = None) -> Path:
    """Return the path to the client's keywords file."""
    return get_client_dir(client_id) / "keywords.md"


def get_context_path(client_id: str = None) -> Path:
    """Return the path to the client's business context file."""
    return get_client_dir(client_id) / "context.md"


def set_active_client(client_id: str) -> None:
    """Set the active client by writing to .active-client file."""
    client_dir = CLIENTS_DIR / client_id
    if not client_dir.is_dir() or not (client_dir / "config.json").exists():
        raise ValueError(
            f"Client '{client_id}' not found.\n"
            f"Available clients: {', '.join(list_clients()) or 'none'}"
        )
    ACTIVE_CLIENT_FILE.write_text(client_id + "\n")


def get_airtable_config(client_id: str = None) -> dict:
    """Return Airtable config for the specified (or active) client. Returns {} if not configured."""
    config = load_config(client_id)
    return config.get("airtable", {})


def is_airtable_enabled(client_id: str = None) -> bool:
    """Return True if Airtable is configured and enabled for the client."""
    at_config = get_airtable_config(client_id)
    return bool(at_config.get("enabled") and at_config.get("base_id"))


def add_client_arg(parser):
    """Add --client argument to an argparse parser."""
    parser.add_argument(
        "--client", default=None,
        help="Client ID to use (overrides .active-client file)"
    )


def resolve_client(args) -> str:
    """Resolve client ID from parsed args (--client flag or .active-client)."""
    if hasattr(args, "client") and args.client:
        return args.client
    return get_active_client()

def get_api_key(client_id: str, service: str) -> str:
    """Return client-specific API key, falling back to global env var."""
    config = load_config(client_id)
    client_key = config.get("api_keys", {}).get(service, "")
    if client_key:
        return client_key
    env_map = {
        "gemini": "GOOGLE_AI_API_KEY",
        "wavespeed_en": "WAVESPEED_API_KEY",
        "wavespeed_ru": "WAVESPEED_API_KEY",
    }
    return os.environ.get(env_map.get(service, ""), "")
