"""
Centralized Supabase client initialization.

This module provides a single point of initialization for the Supabase client
using a singleton pattern to avoid duplicate client creation.
"""
import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

# Global client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create the Supabase client instance.

    This function implements a singleton pattern to ensure only one
    Supabase client is created throughout the application lifecycle.

    Returns:
        Client: The initialized Supabase client instance
    """
    global _supabase_client

    if _supabase_client is None:
        # Load environment variables
        load_dotenv()

        # Get Supabase credentials from environment
        url: str = os.getenv("supabaseUrl")  # type: ignore
        key: str = os.getenv("supabaseKey")  # type: ignore

        # Create the client
        _supabase_client = create_client(url, key)

    return _supabase_client
