import aiosqlite
from pathlib import Path

DB_PATH = Path("upi_mesh.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                vpa TEXT PRIMARY KEY,
                name TEXT,
                balance REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                packet_hash TEXT UNIQUE,
                sender TEXT,
                receiver TEXT,
                amount REAL,
                status TEXT,
                created_at TEXT
            )
        """)
        # Seed demo accounts
        await db.execute("INSERT OR IGNORE INTO accounts VALUES (?, ?, ?)", 
                         ("alice@upi", "Alice", 5000.0))
        await db.execute("INSERT OR IGNORE INTO accounts VALUES (?, ?, ?)", 
                         ("bob@upi", "Bob", 3000.0))
        await db.execute("INSERT OR IGNORE INTO accounts VALUES (?, ?, ?)", 
                         ("charlie@upi", "Charlie", 2000.0))
        await db.commit()

async def get_accounts():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM accounts")
        return [dict(row) for row in await cursor.fetchall()]

async def settle_payment(packet_hash: str, sender: str, receiver: str, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO transactions (packet_hash, sender, receiver, amount, status, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (packet_hash, sender, receiver, amount, "SETTLED")
            )
        except aiosqlite.IntegrityError:
            return {"status": "DUPLICATE", "message": "Packet already settled"}

        cursor = await db.execute("SELECT balance FROM accounts WHERE vpa = ?", (sender,))
        row = await cursor.fetchone()
        if not row or row[0] < amount:
            await db.execute("UPDATE transactions SET status = ? WHERE packet_hash = ?", 
                             ("REJECTED_INSUFFICIENT", packet_hash))
            await db.commit()
            return {"status": "REJECTED", "message": "Insufficient balance"}

        await db.execute("UPDATE accounts SET balance = balance - ? WHERE vpa = ?", (amount, sender))
        await db.execute("UPDATE accounts SET balance = balance + ? WHERE vpa = ?", (amount, receiver))
        await db.commit()
        return {"status": "SETTLED", "message": f"₹{amount} transferred from {sender} to {receiver}"}