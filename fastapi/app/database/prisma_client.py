"""
Clean Prisma Client for FastAPI - connects to the same database as your NestJS backend.
"""
import os
import asyncio
from typing import Optional
from prisma import Prisma, register

# Register Prisma client for async usage
register(Prisma())

class PrismaManager:
    """Manages Prisma client connection for FastAPI."""
    
    def __init__(self):
        self.client: Optional[Prisma] = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """Connect to the database."""
        async with self._lock:
            if not self.client:
                self.client = Prisma()
                await self.client.connect()
                print("✅ Connected to PostgreSQL database via Prisma")
    
    async def disconnect(self):
        """Disconnect from the database."""
        async with self._lock:
            if self.client:
                await self.client.disconnect()
                self.client = None
                print("🔌 Disconnected from database")
    
    def get_client(self) -> Prisma:
        """Get the Prisma client."""
        if not self.client:
            raise RuntimeError("Prisma client not connected. Call connect() first.")
        return self.client

# Global Prisma manager instance
prisma_manager = PrismaManager()

async def get_prisma() -> Prisma:
    """FastAPI dependency to get Prisma client."""
    return prisma_manager.get_client()
