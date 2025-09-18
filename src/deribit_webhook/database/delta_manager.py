"""
Delta record database manager

Uses aiosqlite to manage Deribit account option positions and unfilled order Delta values.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import aiosqlite

from ..config import settings
from .types import (
    DeltaRecord,
    CreateDeltaRecordInput,
    UpdateDeltaRecordInput,
    DeltaRecordQuery,
    DeltaRecordStats,
    AccountDeltaSummary,
    InstrumentDeltaSummary,
    DeltaRecordType
)


class DeltaManager:
    """
    Delta record database manager
    Uses aiosqlite to manage Deribit account option positions and unfilled order Delta values
    """
    
    _instance: Optional['DeltaManager'] = None
    
    def __init__(self, db_path: Optional[str] = None):
        if DeltaManager._instance is not None:
            raise RuntimeError("DeltaManager is a singleton. Use get_instance() instead.")
        
        # Default database path
        if db_path is None:
            db_path = "./data/delta_records.db"
        
        self.db_path = Path(db_path).resolve()
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._initialized = False
        DeltaManager._instance = self
    
    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> 'DeltaManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance
    
    async def initialize(self):
        """Initialize database tables"""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better performance
            await db.execute("PRAGMA journal_mode = WAL")
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Create tables
            await self._create_tables(db)
            await db.commit()
        
        self._initialized = True
        print(f"✅ Delta database initialized: {self.db_path}")
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create database tables"""
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS delta_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                instrument_name TEXT NOT NULL,
                order_id TEXT,
                target_delta REAL NOT NULL CHECK (target_delta >= -1 AND target_delta <= 1),
                move_position_delta REAL NOT NULL DEFAULT 0 CHECK (move_position_delta >= -1 AND move_position_delta <= 1),
                min_expire_days INTEGER CHECK (min_expire_days IS NULL OR min_expire_days > 0),
                tv_id INTEGER,
                action TEXT CHECK (action IN ('open_long', 'open_short', 'close_long', 'close_short', 'reduce_long', 'reduce_short', 'stop_long', 'stop_short')),
                record_type TEXT NOT NULL CHECK (record_type IN ('position', 'order')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        await db.execute(create_table_sql)
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_account_id ON delta_records(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_instrument_name ON delta_records(instrument_name)",
            "CREATE INDEX IF NOT EXISTS idx_order_id ON delta_records(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_tv_id ON delta_records(tv_id)",
            "CREATE INDEX IF NOT EXISTS idx_action ON delta_records(action)",
            "CREATE INDEX IF NOT EXISTS idx_record_type ON delta_records(record_type)",
            "CREATE INDEX IF NOT EXISTS idx_account_instrument ON delta_records(account_id, instrument_name)",
            # Unique constraint: only one position record per account per instrument
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_position ON delta_records(account_id, instrument_name) WHERE record_type = 'position'",
            # Unique constraint: only one record per order ID
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_order ON delta_records(order_id) WHERE order_id IS NOT NULL"
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
        
        # Create trigger for automatic updated_at update
        trigger_sql = """
            CREATE TRIGGER IF NOT EXISTS update_delta_records_timestamp 
            AFTER UPDATE ON delta_records
            BEGIN
                UPDATE delta_records SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """
        
        await db.execute(trigger_sql)
    
    async def create_record(self, input_data: CreateDeltaRecordInput) -> DeltaRecord:
        """Create a new Delta record"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO delta_records (
                    account_id, instrument_name, order_id, target_delta, 
                    move_position_delta, min_expire_days, tv_id, action, record_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                input_data.account_id,
                input_data.instrument_name,
                input_data.order_id,
                input_data.target_delta,
                input_data.move_position_delta,
                input_data.min_expire_days,
                input_data.tv_id,
                input_data.action,
                input_data.record_type.value
            ))
            
            record_id = cursor.lastrowid
            await db.commit()
            
            # Fetch the created record
            return await self.get_record_by_id(record_id)
    
    async def get_record_by_id(self, record_id: int) -> Optional[DeltaRecord]:
        """Get Delta record by ID"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM delta_records WHERE id = ?", 
                (record_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_delta_record(row)
            return None
    
    async def update_record(self, record_id: int, input_data: UpdateDeltaRecordInput) -> Optional[DeltaRecord]:
        """Update Delta record"""
        await self.initialize()
        
        # Build update query dynamically
        update_fields = []
        values = []
        
        for field, value in input_data.model_dump(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = ?")
                values.append(value)
        
        if not update_fields:
            return await self.get_record_by_id(record_id)
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(record_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE delta_records SET {', '.join(update_fields)} WHERE id = ?",
                values
            )
            await db.commit()
            
            return await self.get_record_by_id(record_id)
    
    async def delete_record(self, record_id: int) -> bool:
        """Delete Delta record"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM delta_records WHERE id = ?", 
                (record_id,)
            )
            await db.commit()
            
            return cursor.rowcount > 0
    
    async def query_records(self, query: DeltaRecordQuery, limit: Optional[int] = None) -> List[DeltaRecord]:
        """Query Delta records"""
        await self.initialize()
        
        # Build WHERE clause dynamically
        where_conditions = []
        values = []
        
        for field, value in query.model_dump(exclude_unset=True).items():
            if value is not None:
                where_conditions.append(f"{field} = ?")
                values.append(value)
        
        where_clause = ""
        if where_conditions:
            where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        limit_clause = ""
        if limit:
            limit_clause = f"LIMIT {limit}"
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"SELECT * FROM delta_records {where_clause} ORDER BY created_at DESC {limit_clause}",
                values
            )
            rows = await cursor.fetchall()
            
            return [self._row_to_delta_record(row) for row in rows]
    
    async def get_stats(self) -> DeltaRecordStats:
        """Get database statistics"""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            # Get total records
            cursor = await db.execute("SELECT COUNT(*) FROM delta_records")
            total_records = (await cursor.fetchone())[0]

            # Get position records
            cursor = await db.execute("SELECT COUNT(*) FROM delta_records WHERE record_type = 'position'")
            position_records = (await cursor.fetchone())[0]

            # Get order records
            cursor = await db.execute("SELECT COUNT(*) FROM delta_records WHERE record_type = 'order'")
            order_records = (await cursor.fetchone())[0]

            # Get unique accounts
            cursor = await db.execute("SELECT DISTINCT account_id FROM delta_records ORDER BY account_id")
            accounts = [row[0] for row in await cursor.fetchall()]

            # Get unique instruments
            cursor = await db.execute("SELECT DISTINCT instrument_name FROM delta_records ORDER BY instrument_name")
            instruments = [row[0] for row in await cursor.fetchall()]

            return DeltaRecordStats(
                total_records=total_records,
                position_records=position_records,
                order_records=order_records,
                accounts=accounts,
                instruments=instruments
            )

    async def get_account_summary(self, account_id: Optional[str] = None) -> List[AccountDeltaSummary]:
        """Get Delta summary grouped by account"""
        await self.initialize()

        where_clause = ""
        values = []
        if account_id:
            where_clause = "WHERE account_id = ?"
            values.append(account_id)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(f"""
                SELECT
                    account_id,
                    SUM(target_delta) as total_delta,
                    SUM(CASE WHEN record_type = 'position' THEN target_delta ELSE 0 END) as position_delta,
                    SUM(CASE WHEN record_type = 'order' THEN target_delta ELSE 0 END) as order_delta,
                    COUNT(*) as record_count
                FROM delta_records
                {where_clause}
                GROUP BY account_id
                ORDER BY account_id
            """, values)

            rows = await cursor.fetchall()

            return [
                AccountDeltaSummary(
                    account_id=row[0],
                    total_delta=row[1] or 0,
                    position_delta=row[2] or 0,
                    order_delta=row[3] or 0,
                    record_count=row[4] or 0
                )
                for row in rows
            ]

    async def get_instrument_summary(self, instrument_name: Optional[str] = None) -> List[InstrumentDeltaSummary]:
        """Get Delta summary grouped by instrument"""
        await self.initialize()

        where_clause = ""
        values = []
        if instrument_name:
            where_clause = "WHERE instrument_name = ?"
            values.append(instrument_name)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(f"""
                SELECT
                    instrument_name,
                    SUM(target_delta) as total_delta,
                    SUM(CASE WHEN record_type = 'position' THEN target_delta ELSE 0 END) as position_delta,
                    SUM(CASE WHEN record_type = 'order' THEN target_delta ELSE 0 END) as order_delta,
                    COUNT(*) as record_count,
                    GROUP_CONCAT(DISTINCT account_id) as accounts
                FROM delta_records
                {where_clause}
                GROUP BY instrument_name
                ORDER BY instrument_name
            """, values)

            rows = await cursor.fetchall()

            return [
                InstrumentDeltaSummary(
                    instrument_name=row[0],
                    total_delta=row[1] or 0,
                    position_delta=row[2] or 0,
                    order_delta=row[3] or 0,
                    record_count=row[4] or 0,
                    accounts=row[5].split(',') if row[5] else []
                )
                for row in rows
            ]

    async def cleanup_old_records(self, days: int = 30) -> int:
        """Clean up old records"""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM delta_records
                WHERE created_at < datetime('now', '-{} days')
            """.format(days))
            await db.commit()

            return cursor.rowcount

    def _row_to_delta_record(self, row: aiosqlite.Row) -> DeltaRecord:
        """Convert database row to DeltaRecord"""
        return DeltaRecord(
            id=row["id"],
            account_id=row["account_id"],
            instrument_name=row["instrument_name"],
            order_id=row["order_id"],
            target_delta=row["target_delta"],
            move_position_delta=row["move_position_delta"],
            min_expire_days=row["min_expire_days"],
            tv_id=row["tv_id"],
            action=row["action"],
            record_type=DeltaRecordType(row["record_type"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
        )


# Global instance
_delta_manager: Optional[DeltaManager] = None


def get_delta_manager(db_path: Optional[str] = None) -> DeltaManager:
    """Get global DeltaManager instance"""
    global _delta_manager
    if _delta_manager is None:
        _delta_manager = DeltaManager.get_instance(db_path)
    return _delta_manager
