import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


DATABASE_PATH = Path(__file__).resolve().parent.parent / "login_system.db"


def build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return f"sqlite:///{DATABASE_PATH.as_posix()}"

    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


ENGINE: Engine = create_engine(build_database_url(), future=True)
IS_POSTGRES = ENGINE.dialect.name == "postgresql"


def execute_optional(statement: str) -> None:
    try:
        with ENGINE.begin() as connection:
            connection.execute(text(statement))
    except SQLAlchemyError:
        pass


def create_tables() -> None:
    user_id_type = "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    purchase_id_type = "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    image_type = "BYTEA" if IS_POSTGRES else "BLOB"

    with ENGINE.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS users (
                    id {user_id_type},
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS milk_packets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    color TEXT NOT NULL,
                    image_path TEXT,
                    image_data {image_type},
                    image_mime TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS milk_purchases (
                    id {purchase_id_type},
                    packet_id TEXT NOT NULL,
                    purchase_date TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(packet_id, purchase_date),
                    FOREIGN KEY(packet_id) REFERENCES milk_packets(id)
                )
                """
            )
        )

        for packet in [
            {"id": "gold", "name": "Gold", "price": 38, "color": "#d9a52f"},
            {"id": "blue", "name": "Blue", "price": 30, "color": "#2878d8"},
            {"id": "green", "name": "Green", "price": 33, "color": "#249b63"},
        ]:
            connection.execute(
                text(
                    """
                    INSERT INTO milk_packets (id, name, price, color)
                    VALUES (:id, :name, :price, :color)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        price = excluded.price,
                        color = excluded.color
                    """
                ),
                packet,
            )

    if not IS_POSTGRES:
        execute_optional("ALTER TABLE milk_packets ADD COLUMN image_data BLOB")
        execute_optional("ALTER TABLE milk_packets ADD COLUMN image_mime TEXT")


def create_user(name: str, email: str, hashed_password: str) -> dict[str, Any]:
    with ENGINE.begin() as connection:
        if IS_POSTGRES:
            user = connection.execute(
                text(
                    """
                    INSERT INTO users (name, email, hashed_password)
                    VALUES (:name, :email, :hashed_password)
                    RETURNING *
                    """
                ),
                {"name": name, "email": email.lower(), "hashed_password": hashed_password},
            ).mappings().fetchone()
        else:
            cursor = connection.execute(
                text(
                    """
                    INSERT INTO users (name, email, hashed_password)
                    VALUES (:name, :email, :hashed_password)
                    """
                ),
                {"name": name, "email": email.lower(), "hashed_password": hashed_password},
            )
            user = connection.execute(
                text("SELECT * FROM users WHERE id = :id"),
                {"id": cursor.lastrowid},
            ).mappings().fetchone()

        if user is None:
            raise RuntimeError("User was not saved correctly")
        return dict(user)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with ENGINE.begin() as connection:
        user = connection.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": email.lower()},
        ).mappings().fetchone()
        return dict(user) if user else None


def list_milk_packets() -> list[dict[str, Any]]:
    with ENGINE.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, name, price, color, image_data IS NOT NULL AS has_image
                FROM milk_packets
                ORDER BY price DESC
                """
            )
        ).mappings().fetchall()
        return [dict(row) for row in rows]


def get_daily_purchases(purchase_date: str) -> list[dict[str, Any]]:
    with ENGINE.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    p.id,
                    p.name,
                    p.price,
                    p.color,
                    p.image_data IS NOT NULL AS has_image,
                    COALESCE(m.quantity, 0) AS quantity
                FROM milk_packets p
                LEFT JOIN milk_purchases m
                    ON m.packet_id = p.id AND m.purchase_date = :purchase_date
                ORDER BY p.price DESC
                """
            ),
            {"purchase_date": purchase_date},
        ).mappings().fetchall()
        return [dict(row) for row in rows]


def add_milk_packet(packet_id: str, purchase_date: str, amount: int = 1) -> None:
    quantity_expression = (
        "GREATEST(0, milk_purchases.quantity + excluded.quantity)"
        if IS_POSTGRES
        else "MAX(0, quantity + excluded.quantity)"
    )
    with ENGINE.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO milk_purchases (packet_id, purchase_date, quantity)
                VALUES (:packet_id, :purchase_date, :amount)
                ON CONFLICT(packet_id, purchase_date) DO UPDATE SET
                    quantity = {quantity_expression},
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"packet_id": packet_id, "purchase_date": purchase_date, "amount": amount},
        )


def set_milk_packet_quantity(packet_id: str, purchase_date: str, quantity: int) -> None:
    with ENGINE.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO milk_purchases (packet_id, purchase_date, quantity)
                VALUES (:packet_id, :purchase_date, :quantity)
                ON CONFLICT(packet_id, purchase_date) DO UPDATE SET
                    quantity = excluded.quantity,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "packet_id": packet_id,
                "purchase_date": purchase_date,
                "quantity": max(0, quantity),
            },
        )


def update_packet_image(packet_id: str, image_data: bytes, image_mime: str) -> bool:
    with ENGINE.begin() as connection:
        cursor = connection.execute(
            text(
                """
                UPDATE milk_packets
                SET image_data = :image_data, image_mime = :image_mime, image_path = NULL
                WHERE id = :packet_id
                """
            ),
            {
                "packet_id": packet_id,
                "image_data": image_data,
                "image_mime": image_mime,
            },
        )
        return cursor.rowcount > 0


def get_packet_image(packet_id: str) -> dict[str, Any] | None:
    with ENGINE.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT image_data, image_mime
                FROM milk_packets
                WHERE id = :packet_id AND image_data IS NOT NULL
                """
            ),
            {"packet_id": packet_id},
        ).mappings().fetchone()

        if row is None:
            return None
        image_data = row["image_data"]
        if isinstance(image_data, memoryview):
            image_data = image_data.tobytes()
        return {"image_data": image_data, "image_mime": row["image_mime"]}


def read_purchase_history(limit: int = 14) -> list[dict[str, Any]]:
    with ENGINE.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    m.purchase_date,
                    SUM(m.quantity) AS packets,
                    SUM(m.quantity * p.price) AS total
                FROM milk_purchases m
                JOIN milk_packets p ON p.id = m.packet_id
                WHERE m.quantity > 0
                GROUP BY m.purchase_date
                ORDER BY m.purchase_date DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().fetchall()
        return [dict(row) for row in rows]
