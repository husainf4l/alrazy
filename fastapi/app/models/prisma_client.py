"""
Prisma Client integration for FastAPI.
This module provides a connection to the same database used by your NestJS backend.
"""
import os
from prisma import Prisma
from typing import Optional

class PrismaManager:
    """Manages Prisma client connection for FastAPI."""
    
    def __init__(self):
        self.client: Optional[Prisma] = None
    
    async def connect(self):
        """Connect to the database."""
        if not self.client:
            self.client = Prisma()
            await self.client.connect()
    
    async def disconnect(self):
        """Disconnect from the database."""
        if self.client:
            await self.client.disconnect()
            self.client = None
    
    def get_client(self) -> Prisma:
        """Get the Prisma client."""
        if not self.client:
            raise RuntimeError("Prisma client not connected. Call connect() first.")
        return self.client

# Global Prisma manager instance
prisma_manager = PrismaManager()

async def get_prisma() -> Prisma:
    """Dependency to get Prisma client."""
    return prisma_manager.get_client()
