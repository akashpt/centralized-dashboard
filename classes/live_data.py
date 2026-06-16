import pymysql
import sqlite3
import traceback
import json
from path import DB_PATH

def get_connection():
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30,
        check_same_thread=False
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def create_tables():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host TEXT,
                user TEXT,
                password TEXT,
                database_name TEXT,
                port INTEGER DEFAULT 3306,
                connect_timeout INTEGER DEFAULT 2,
                company_id TEXT DEFAULT NULL,
                status INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                updated_at DATETIME DEFAULT (datetime('now', 'localtime')) 
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT,
                page_name TEXT,
                password TEXT,
                created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                updated_at DATETIME DEFAULT (datetime('now', 'localtime')) 
            )
        """)

        conn.commit()

def fetch_one(query, values=None):
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            if values is not None:
                cur.execute(query, values)
            else:
                cur.execute(query)

            return cur.fetchone()

    except Exception as e:
        print("DB fetch_one error:", e)
        return False
    
def get_dashboard_data():
    row = fetch_one("""
        SELECT
            id,
            host,
            user,
            password,
            database_name,
            port,
            connect_timeout,
            status,
            company_id
        FROM dashboard_data
        WHERE status = 1
        ORDER BY id DESC
        LIMIT 1
    """)

    if not row:
        return {}

    return {
        "id": row[0],
        "host": row[1],
        "user": row[2],
        "password": row[3],
        "database_name": row[4],
        "port": row[5] or 3306,
        "connect_timeout": row[6] or 2,
        "status": row[7] or 0,
        "company_id": row[8] or None
    }



def get_mysql_connection():
    try:
        data = get_dashboard_data()

        if not data:
            print("❌ No active dashboard DB config found")
            return None,None
        company_id = data.get("company_id","")
        return pymysql.connect(
            host=data["host"],
            user=data["user"],
            password=data["password"],
            database=data["database_name"],
            port=int(data["port"]),
            connect_timeout=int(data["connect_timeout"]),
            autocommit=False,
            charset="utf8mb4",
        ),company_id
    except Exception as e:
        print("❌ Connection Error")
        traceback.print_exc()
        return None, None
    
def safe_json_load(value, default):
    try:
        if not value:
            return default
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)
    except Exception:
        return default


def fetch_live_machines():
    conn, company_id = get_mysql_connection()

    if conn is None:
        return []

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("""
                SELECT
                    id,
                    machine_no,
                    company_id,
                    device_id,
                    live_datas,
                    report_datas,
                    machine_status,
                    status,
                    created_at,
                    updated_at
                FROM live_doff_details
                WHERE status = 1
                  AND company_id = %s
                ORDER BY machine_no ASC
            """, (company_id,))

            rows = cur.fetchall()

        machines = []

        for row in rows:
            machines.append({
                "id": row.get("id"),
                "machine_no": row.get("machine_no"),
                "company_id": row.get("company_id"),
                "device_id": row.get("device_id"),
                "live_datas": safe_json_load(row.get("live_datas"), {}),
                "report_datas": safe_json_load(row.get("report_datas"), []),
                "machine_status": row.get("machine_status") or "STOPPED",
                "status": row.get("status") or 0,
                "created_at": str(row.get("created_at") or ""),
                "updated_at": str(row.get("updated_at") or ""),
            })

        return machines

    except Exception:
        traceback.print_exc()
        return []

    finally:
        conn.close()


def get_user(user_name):
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    user_name,
                    password,
                    page_name
                FROM user_table
                WHERE user_name = ?
                LIMIT 1
            """, (user_name,))

            row = cur.fetchone()

            if not row:
                return None

            return {
                "user_name": row[0],
                "password": row[1],
                "page_name": row[2]
            }

    except Exception as e:
        print("get_user error:", e)
        return None

    
