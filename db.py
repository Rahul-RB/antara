import json
import os
import sqlite3
import typing

from config import DB_PATH, IMAGE_CACHE_DIR


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS confirmed_matches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            an_id       TEXT NOT NULL,
            as_id       TEXT NOT NULL,
            confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(an_id, as_id)
        );

        CREATE TABLE IF NOT EXISTS profile_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            site        TEXT NOT NULL,
            profile_id  TEXT NOT NULL,
            url_id      TEXT,
            name        TEXT,
            age         INTEGER,
            height_cm   INTEGER,
            nakshatra   TEXT,
            rashi       TEXT,
            gotra       TEXT,
            paada       TEXT,
            raw_data    TEXT,
            last_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(site, profile_id)
        );

        CREATE TABLE IF NOT EXISTS image_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            site        TEXT NOT NULL,
            profile_id  TEXT NOT NULL,
            image_url   TEXT NOT NULL,
            local_path  TEXT,
            embedding   TEXT,
            cached_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(site, profile_id, image_url)
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            status      TEXT NOT NULL DEFAULT 'pending',
            source_site TEXT NOT NULL,
            source_id   TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result      TEXT,
            error       TEXT
        );
    """)
    conn.commit()
    conn.close()


def get_confirmed_match(source_site: str, source_id: str) -> dict[str, typing.Any] | None:
    conn = get_conn()
    if source_site == "an":
        row = conn.execute(
            "SELECT as_id FROM confirmed_matches WHERE an_id = ?", (source_id,)
        ).fetchone()
        conn.close()
        return {"as_id": row["as_id"]} if row else None

    row = conn.execute(
        "SELECT an_id FROM confirmed_matches WHERE as_id = ?", (source_id,)
    ).fetchone()
    conn.close()
    return {"an_id": row["an_id"]} if row else None


def save_confirmed_match(an_id: str, as_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO confirmed_matches (an_id, as_id) VALUES (?, ?)", (an_id, as_id)
    )
    conn.commit()
    conn.close()


def upsert_profile(site: str, profile_id: str, data: dict) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO profile_cache (site, profile_id, url_id, name, age, height_cm,
            nakshatra, rashi, gotra, paada, raw_data, last_scraped)
        VALUES (:site, :profile_id, :url_id, :name, :age, :height_cm,
            :nakshatra, :rashi, :gotra, :paada, :raw_data, CURRENT_TIMESTAMP)
        ON CONFLICT(site, profile_id) DO UPDATE SET
            url_id=excluded.url_id, name=excluded.name, age=excluded.age,
            height_cm=excluded.height_cm, nakshatra=excluded.nakshatra,
            rashi=excluded.rashi, gotra=excluded.gotra, paada=excluded.paada,
            raw_data=excluded.raw_data, last_scraped=excluded.last_scraped
    """,
        {
            "site": site,
            "profile_id": profile_id,
            "url_id": data.get("url_id"),
            "name": data.get("name"),
            "age": data.get("age"),
            "height_cm": data.get("height_cm"),
            "nakshatra": data.get("nakshatra"),
            "rashi": data.get("rashi"),
            "gotra": data.get("gotra"),
            "paada": data.get("paada"),
            "raw_data": json.dumps(data),
        },
    )
    conn.commit()
    conn.close()


def get_cached_embeddings(site: str, profile_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT image_url, local_path, embedding FROM image_cache "
        "WHERE site=? AND profile_id=? AND embedding IS NOT NULL",
        (site, profile_id),
    ).fetchall()
    conn.close()
    return [
        {
            "image_url": r["image_url"],
            "local_path": r["local_path"],
            "embedding": json.loads(r["embedding"]),
        }
        for r in rows
    ]


def save_image_cache(
    site: str,
    profile_id: str,
    image_url: str,
    local_path: str | None,
    embedding: list[float] | None,
) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO image_cache (site, profile_id, image_url, local_path, embedding)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(site, profile_id, image_url) DO UPDATE SET
            local_path=excluded.local_path, embedding=excluded.embedding,
            cached_at=CURRENT_TIMESTAMP
    """,
        (
            site,
            profile_id,
            image_url,
            local_path,
            json.dumps(embedding) if embedding is not None else None,
        ),
    )
    conn.commit()
    conn.close()


def create_job(job_id: str, source_site: str, source_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO jobs (id, status, source_site, source_id) VALUES (?, ?, ?, ?)",
        (job_id, "pending", source_site, source_id),
    )
    conn.commit()
    conn.close()


def update_job(
    job_id: str, status: str, result: typing.Any = None, error: typing.Any = None
) -> None:
    conn = get_conn()
    conn.execute(
        """
        UPDATE jobs SET status=?, result=?, error=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """,
        (status, json.dumps(result) if result is not None else None, error, job_id),
    )
    conn.commit()
    conn.close()


def get_job(job_id: str) -> dict[str, dict[typing.Any, typing.Any]] | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("result"):
        d["result"] = json.loads(d["result"])
    return d
