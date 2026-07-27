"""Jarvis Application Immutable Constants."""

APP_NAME = "Jarvis AI Assistant"
APP_VERSION = "0.1.0"
API_VERSION_PREFIX = "/api/v1"

# Vector Database Collections
DEFAULT_VECTOR_COLLECTION = "jarvis_knowledge_base"
DEFAULT_EMBEDDING_DIMENSION = 1536

# System Defaults
DEFAULT_HTTP_TIMEOUT_SECONDS = 30
DEFAULT_MAX_CONCURRENT_TASKS = 10
DEFAULT_USER_AGENT = f"Jarvis-Agent/{APP_VERSION}"

# Banner
JARVIS_BANNER = f"""
===================================================================
     🤖 {APP_NAME} - Version {APP_VERSION}
     Production-Grade Autonomous Clean Architecture AI System
===================================================================
"""
