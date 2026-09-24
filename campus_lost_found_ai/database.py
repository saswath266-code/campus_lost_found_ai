import os
from datetime import datetime

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()
class DatabaseError(Exception):
    """Custom database exception."""
    pass


# =========================================================
# DATABASE CONNECTION
# =========================================================

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
}


DB_NAME = os.getenv("MYSQL_DATABASE", "campus_lost_found")
ITEM_STATUSES = [
    "searching",
    "potential_match",
    "verification_pending",
    "verified",
    "returned",
    "rejected"
]
ITEM_TYPES = [
    "lost",
    "found"
]

def get_connection(database=True):
    config = DB_CONFIG.copy()

    if database:
        config["database"] = DB_NAME

    return mysql.connector.connect(**config)


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def init_db():

    try:
        # ---------------------------------------------
        # Create database
        # ---------------------------------------------
        conn = get_connection(database=False)
        cursor = conn.cursor()

        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`"
        )

        cursor.close()
        conn.close()

        # ---------------------------------------------
        # Connect to created database
        # ---------------------------------------------
        conn = get_connection()
        cursor = conn.cursor()

        # ---------------------------------------------
        # ITEMS TABLE
        # ---------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INT AUTO_INCREMENT PRIMARY KEY,

                type VARCHAR(20) NOT NULL,

                name VARCHAR(255) NOT NULL,

                category VARCHAR(100),

                description TEXT,

                private_details TEXT,

                location VARCHAR(255),

                event_time VARCHAR(100),

                image VARCHAR(500),

                status VARCHAR(50) DEFAULT 'searching',

                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---------------------------------------------
        # CLAIMS TABLE
        # ---------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id INT AUTO_INCREMENT PRIMARY KEY,

                item_id INT NOT NULL,

                claimant_name VARCHAR(255) NOT NULL,

                claimant_id VARCHAR(100),

                proof_type VARCHAR(100),

                proof_details TEXT,

                verification_status VARCHAR(50)
                    DEFAULT 'pending',

                office_remarks TEXT,

                created_at DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                verified_at DATETIME,

                verified_by VARCHAR(255),

                FOREIGN KEY (item_id)
                    REFERENCES items(id)
                    ON DELETE CASCADE
            )
        """)
        # ---------------------------------------------
        # MATCH REVIEWS TABLE
        # ---------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_reviews (

                id INT AUTO_INCREMENT PRIMARY KEY,

                item_id INT NOT NULL,

                candidate_id INT NOT NULL,

                image_score FLOAT DEFAULT 0,

                text_score FLOAT DEFAULT 0,

                location_score FLOAT DEFAULT 0,

                time_score FLOAT DEFAULT 0,

                overall_score FLOAT DEFAULT 0,

                explanation TEXT,

                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                UNIQUE KEY unique_match (
                    item_id,
                    candidate_id
                ),

                FOREIGN KEY (item_id)
                    REFERENCES items(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (candidate_id)
                    REFERENCES items(id)
                    ON DELETE CASCADE
            )
    """)

        conn.commit()

        cursor.close()
        conn.close()

        print("MySQL database initialized successfully.")

    except Error as e:
        print("Database initialization error:", e)


# =========================================================
# ADD ITEM
# =========================================================

# =========================================================
# ADD ITEM
# =========================================================

def add_item(
    item_type,
    name,
    category,
    description,
    location,
    event_time,
    image,
    private_details=""
):
    """
    Add a lost/found item.

    private_details is optional so the existing app.py
    continues to work.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:

        query = """
            INSERT INTO items
            (
                type,
                name,
                category,
                description,
                private_details,
                location,
                event_time,
                image,
                status,
                created_at
            )
            VALUES
            (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        """

        values = (
            item_type,
            name,
            category,
            description,
            private_details,
            location,
            event_time,
            image,
            "searching",
            datetime.now()
        )

        cursor.execute(query, values)

        item_id = cursor.lastrowid

        conn.commit()

        return item_id

    except Error as exc:

        conn.rollback()

        raise DatabaseError(
            f"Could not add item: {exc}"
        ) from exc

    finally:

        cursor.close()
        conn.close()


# =========================================================
# GET SINGLE ITEM
# =========================================================

def get_item(item_id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM items
        WHERE id = %s
        """,
        (item_id,)
    )

    item = cursor.fetchone()

    cursor.close()
    conn.close()

    return item


# =========================================================
# GET ALL ITEMS
# =========================================================

# =========================================================
# GET ITEMS
# =========================================================

def get_items(
    item_type=None,
    query=None,
    category=None,
    limit=50
):
    """
    Get items with optional filtering.

    Supports calls such as:

        get_items()

        get_items("lost")

        get_items(
            "lost",
            query="phone",
            category="Mobile Phone",
            limit=12
        )
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        sql = """
            SELECT *
            FROM items
            WHERE 1 = 1
        """

        params = []

        # -------------------------------------------------
        # Filter by lost/found
        # -------------------------------------------------

        if item_type:
            sql += """
                AND type = %s
            """
            params.append(item_type)

        # -------------------------------------------------
        # Search text
        # -------------------------------------------------

        if query:
            search = f"%{query.strip()}%"

            sql += """
                AND (
                    name LIKE %s
                    OR category LIKE %s
                    OR description LIKE %s
                    OR location LIKE %s
                )
            """

            params.extend([
                search,
                search,
                search,
                search
            ])

        # -------------------------------------------------
        # Filter category
        # -------------------------------------------------

        if category:
            sql += """
                AND category = %s
            """
            params.append(category)

        # -------------------------------------------------
        # Don't show returned/rejected items
        # -------------------------------------------------

        sql += """
            AND status NOT IN ('returned', 'rejected')
        """

        # -------------------------------------------------
        # Newest first
        # -------------------------------------------------

        sql += """
            ORDER BY created_at DESC
            LIMIT %s
        """

        # MySQL connector requires LIMIT as parameter
        params.append(int(limit))

        cursor.execute(sql, tuple(params))

        return cursor.fetchall()

    except Error as exc:

        raise DatabaseError(
            f"Could not get items: {exc}"
        ) from exc

    finally:

        cursor.close()
        conn.close()


# =========================================================
# GET OPPOSITE TYPE ITEMS
# =========================================================

def get_matching_items(item_type):

    opposite_type = (
        "found"
        if item_type == "lost"
        else "lost"
    )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM items
        WHERE type = %s
        AND status NOT IN ('returned', 'rejected')
        ORDER BY created_at DESC
        """,
        (opposite_type,)
    )

    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return items


# =========================================================
# UPDATE ITEM STATUS
# =========================================================

def update_status(item_id, status):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE items
        SET status = %s
        WHERE id = %s
        """,
        (status, item_id)
    )

    conn.commit()

    cursor.close()
    conn.close()


# =========================================================
# CREATE CLAIM
# =========================================================

def create_claim(
    item_id,
    claimant_name,
    claimant_id,
    proof_type,
    proof_details
):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO claims
        (
            item_id,
            claimant_name,
            claimant_id,
            proof_type,
            proof_details,
            verification_status,
            created_at
        )
        VALUES
        (
            %s, %s, %s, %s, %s, %s, %s
        )
    """

    values = (
        item_id,
        claimant_name,
        claimant_id,
        proof_type,
        proof_details,
        "pending",
        datetime.now()
    )

    cursor.execute(query, values)

    claim_id = cursor.lastrowid

    conn.commit()

    cursor.close()
    conn.close()

    return claim_id


# =========================================================
# GET CLAIM
# =========================================================

def get_claim(claim_id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            c.*,
            i.name AS item_name,
            i.type AS item_type,
            i.category,
            i.description,
            i.private_details,
            i.location,
            i.event_time,
            i.image,
            i.status AS item_status
        FROM claims c
        JOIN items i
            ON c.item_id = i.id
        WHERE c.id = %s
        """,
        (claim_id,)
    )

    claim = cursor.fetchone()

    cursor.close()
    conn.close()

    return claim


# =========================================================
# GET ALL CLAIMS
# =========================================================

def get_claims():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.*,
            i.name AS item_name,
            i.type AS item_type,
            i.image,
            i.status AS item_status
        FROM claims c
        JOIN items i
            ON c.item_id = i.id
        ORDER BY c.created_at DESC
    """)

    claims = cursor.fetchall()

    cursor.close()
    conn.close()

    return claims


# =========================================================
# GET PENDING CLAIMS
# =========================================================

def get_pending_claims():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.*,
            i.name AS item_name,
            i.type AS item_type,
            i.category,
            i.description,
            i.private_details,
            i.location,
            i.event_time,
            i.image,
            i.status AS item_status
        FROM claims c
        JOIN items i
            ON c.item_id = i.id
        WHERE c.verification_status = 'pending'
        ORDER BY c.created_at ASC
    """)

    claims = cursor.fetchall()

    cursor.close()
    conn.close()

    return claims


# =========================================================
# UPDATE CLAIM STATUS
# =========================================================

def update_claim_status(
    claim_id,
    verification_status,
    office_remarks="",
    verified_by=None
):

    conn = get_connection()
    cursor = conn.cursor()

    if verification_status == "verified":

        cursor.execute(
            """
            UPDATE claims
            SET
                verification_status = %s,
                office_remarks = %s,
                verified_at = %s,
                verified_by = %s
            WHERE id = %s
            """,
            (
                verification_status,
                office_remarks,
                datetime.now(),
                verified_by,
                claim_id
            )
        )

    else:

        cursor.execute(
            """
            UPDATE claims
            SET
                verification_status = %s,
                office_remarks = %s
            WHERE id = %s
            """,
            (
                verification_status,
                office_remarks,
                claim_id
            )
        )

    conn.commit()

    cursor.close()
    conn.close()


# =========================================================
# CHECK EXISTING CLAIM
# =========================================================

def has_pending_claim(item_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM claims
        WHERE item_id = %s
        AND verification_status = 'pending'
        """,
        (item_id,)
    )

    count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return count > 0
# =========================================================
# GET MATCH REVIEW
# =========================================================

# =========================================================
# GET MATCH REVIEW
# =========================================================

def get_match_review(lost_item_id, found_item_id):
    """
    Get the cached AI review for a lost/found pair.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT *
            FROM match_reviews
            WHERE lost_item_id = %s
              AND found_item_id = %s
            LIMIT 1
            """,
            (lost_item_id, found_item_id)
        )

        return cursor.fetchone()

    except Error as exc:
        raise DatabaseError(
            f"Could not get match review: {exc}"
        ) from exc

    finally:
        cursor.close()
        conn.close()


# =========================================================
# SAVE MATCH REVIEW
# =========================================================

# =========================================================
# SAVE MATCH REVIEW
# =========================================================

def save_match_review(
    lost_item_id,
    found_item_id,
    input_fingerprint,
    assessment,
    confidence
):
    """
    Save an AI match analysis using the existing
    match_reviews table schema.

    Parameters:
        lost_item_id      - ID of lost report
        found_item_id    - ID of found report
        input_fingerprint - fingerprint of the compared inputs
        assessment       - Gemini analysis dictionary
        confidence       - AI evidence confidence
    """

    import json

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # Convert Gemini assessment dictionary to JSON
        if isinstance(assessment, str):
            analysis_json = assessment
        else:
            analysis_json = json.dumps(
                assessment,
                ensure_ascii=False
            )

        # Keep confidence safely inside 0-100
        try:
            confidence_value = int(confidence)
        except (TypeError, ValueError):
            confidence_value = 0

        confidence_value = max(
            0,
            min(100, confidence_value)
        )

        cursor.execute(
            """
            INSERT INTO match_reviews
            (
                lost_item_id,
                found_item_id,
                input_fingerprint,
                analysis_json,
                evidence_confidence,
                analysis_state,
                decision,
                created_at,
                updated_at
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                'completed',
                'potential',
                NOW(),
                NOW()
            )
            ON DUPLICATE KEY UPDATE
                input_fingerprint = VALUES(input_fingerprint),
                analysis_json = VALUES(analysis_json),
                evidence_confidence = VALUES(evidence_confidence),
                analysis_state = 'completed',
                updated_at = NOW()
            """,
            (
                lost_item_id,
                found_item_id,
                input_fingerprint,
                analysis_json,
                confidence_value
            )
        )

        conn.commit()

        return cursor.lastrowid

    except Error as exc:

        conn.rollback()

        raise DatabaseError(
            f"Could not save match review: {exc}"
        ) from exc

    finally:

        cursor.close()
        conn.close()

# =========================================================
# GET MATCH REVIEW BY ID
# =========================================================

def get_match_review_by_id(item_id):
    """
    Get an item and its possible opposite-type matches
    for the office review page.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get the main item
        cursor.execute(
            """
            SELECT *
            FROM items
            WHERE id = %s
            """,
            (item_id,)
        )

        item = cursor.fetchone()

        if not item:
            return None

        # Find opposite type
        opposite_type = (
            "found"
            if item["type"] == "lost"
            else "lost"
        )

        cursor.execute(
            """
            SELECT *
            FROM items
            WHERE type = %s
              AND id != %s
              AND status NOT IN ('returned', 'rejected')
            ORDER BY created_at DESC
            """,
            (opposite_type, item_id)
        )

        candidates = cursor.fetchall()

        return {
            "item": item,
            "candidates": candidates
        }

    except Error as exc:
        raise DatabaseError(
            f"Could not load match review: {exc}"
        ) from exc

    finally:
        cursor.close()
        conn.close()

def set_match_decision(item_id, decision, notes=""):
    """
    Update the office decision/status for an item.
    """

    if decision not in ITEM_STATUSES:
        raise DatabaseError(
            f"Invalid item status: {decision}"
        )

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE items
            SET status = %s
            WHERE id = %s
            """,
            (decision, item_id)
        )

        conn.commit()

    except Error as exc:
        conn.rollback()

        raise DatabaseError(
            f"Could not set match decision: {exc}"
        ) from exc

    finally:
        cursor.close()
        conn.close()