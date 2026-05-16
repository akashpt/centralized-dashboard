
import mysql.connector 
from datetime import datetime, timedelta
import json
import sqlite3

# --- MySQL connection ---
def get_mysql_connection():
    try:
        return mysql.connector.connect(
            host="3.111.67.90",
            user="root",
            port=3306,
            password="TexaAdmin",
            database="fab_vi",
            connection_timeout=2,   # 🔥 MUST HAVE
            use_pure=True        # 🔥 prevents Windows hang
        )
    except Exception as e:
        print("❌ MySQL connection failed:", e)
        return None

def get_db_data(machine_no):
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT datas, running_time, ideal_time "
            "FROM machine_performence WHERE machine_no = %s",
            (machine_no,),
        )
        row = cursor.fetchone()

        if row and row.get("datas"):
            data_dict = json.loads(row["datas"])

            # attach running_time JSON list if present
            if row.get("running_time"):
                try:
                    data_dict["running_time"] = json.loads(row["running_time"])
                except json.JSONDecodeError:
                    data_dict["running_time"] = []

            # attach ideal_time JSON list if present
            if row.get("ideal_time"):
                try:
                    data_dict["ideal_time"] = json.loads(row["ideal_time"])
                except json.JSONDecodeError:
                    data_dict["ideal_time"] = []

            return data_dict
        else:
            print(f"No data found for machine_no={machine_no}")
            return {}
    finally:
        conn.close()

# def get_db_machines():
#     conn = get_mysql_connection()
#     if conn is None:
#         print("⚠ MySQL not reachable, returning empty machine list")
#         return []

#     try:
#         cursor = conn.cursor(dictionary=True, buffered=True)
#         cursor.execute(
#             "SELECT machine_no, status FROM machine_performence ORDER BY machine_no"
#         )
#         return cursor.fetchall() or []
#     except Exception as e:
#         print("❌ get_db_machines error:", e)
#         return []
#     finally:
#         conn.close()
def get_db_machines():
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT machine_no, status FROM machine_performence ORDER BY machine_no"
        )
        rows = cursor.fetchall()

        # ✅ FORCE 2-digit machine numbers (03, 04, 12)
        for r in rows:
            r["machine_no"] = f"{int(r['machine_no']):02d}"

        return rows
    finally:
        conn.close()



# ---------- ALL report: start_timing_table for all machines ----------
def get_db_all_start_data():
    conn = get_mysql_connection()   
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT DISTINCT machine_no FROM machine_performence ORDER BY machine_no")
        machine_rows = cur.fetchall()
    finally:
        conn.close()

    machine_nos = [row["machine_no"] for row in machine_rows]
    combined = []

    for m_no in machine_nos:
        data = get_db_data(m_no) or {}
        mp = data.get("machine_performence") or {}
        start_rows = mp.get("start_timing_table") or []

        for sr in start_rows:
            sr_copy = dict(sr)
            if not (
                "machine_number" in sr_copy
                or "machine" in sr_copy
                or "machine_no" in sr_copy
            ):
                sr_copy["machine_number"] = m_no
            combined.append(sr_copy)

    return {"machine_performence": {"start_timing_table": combined}}


# ---------- ALL machine_performance (running/ideal/defects for ALL) ----------
def get_db_all_machine_performance():
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT machine_no, datas, running_time, ideal_time "
            "FROM machine_performence"
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    combined_start   = []
    combined_running = []
    combined_ideal   = []
    combined_defects = []   # <-- NEW: all defect_logs across machines

    for row in rows:
        m_no = row["machine_no"]

        # Parse datas JSON once
        datas = row.get("datas")
        data_dict = {}
        if datas:
            try:
                data_dict = json.loads(datas)
            except json.JSONDecodeError:
                data_dict = {}

        mp = (
            data_dict.get("machine_performence")
            or data_dict.get("machine_performance")
            or {}
        )

        # --- start_timing_table ---
        start_rows = mp.get("start_timing_table") or []
        for sr in start_rows:
            sr_copy = dict(sr)
            if (
                "machine_number" not in sr_copy
                and "machine" not in sr_copy
                and "machine_no" not in sr_copy
            ):
                sr_copy["machine_number"] = m_no
            combined_start.append(sr_copy)

        # --- defect_logs inside datas root (added by update_defect_logs_for_one_machine) ---
        defect_rows = data_dict.get("defect_logs") or []
        for d in defect_rows:
            d_copy = dict(d)
            # tag with machine_no so frontend can separate machines
            d_copy["machine_no"] = m_no
            combined_defects.append(d_copy)

        # --- running_time column ---
        if row.get("running_time"):
            try:
                run_list = json.loads(row["running_time"])
            except json.JSONDecodeError:
                run_list = []
            for it in run_list:
                it_copy = dict(it)
                it_copy["machine_no"] = m_no
                combined_running.append(it_copy)

        # --- ideal_time column ---
        if row.get("ideal_time"):
            try:
                idle_list = json.loads(row["ideal_time"])
            except json.JSONDecodeError:
                idle_list = []
            for it in idle_list:
                it_copy = dict(it)
                it_copy["machine_no"] = m_no
                combined_ideal.append(it_copy)

    combined_running.sort(key=lambda r: r.get("machine_no", 0))
    combined_ideal.sort(key=lambda r: r.get("machine_no", 0))

    return {
        "machine_performence": {"start_timing_table": combined_start},
        "running_time": combined_running,
        "ideal_time": combined_ideal,
        "defect_logs": combined_defects,   # <-- NEW
    }


# ---------- read from SQLite + update MySQL (ideal_time) ----------
def update_ideal_time_for_one_machine(sqlite_db_path, machine_no):
    conn_sqlite = sqlite3.connect(sqlite_db_path)
    cur_sqlite = conn_sqlite.cursor()

    query = """
        SELECT
            roll_id,
            SUM(strftime('%s', end_time) - strftime('%s', start_time)) AS total_seconds
        FROM idle_logs
        GROUP BY roll_id
        ORDER BY roll_id;
    """
    cur_sqlite.execute(query)

    idle_list = []

    for roll_id, total_seconds in cur_sqlite.fetchall():
        if total_seconds is None:
            continue

        total_seconds = int(total_seconds)
        hrs = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        idle_list.append({
            "roll_id": roll_id,
            "ideal_time": f"{hrs:02d}:{mins:02d}:{secs:02d}"
        })

    conn_sqlite.close()

    idle_json_str = json.dumps(idle_list)

    conn_mysql = get_mysql_connection()
    cursor = conn_mysql.cursor()

    update_sql = """
        UPDATE machine_performence
        SET ideal_time = %s
        WHERE machine_no = %s
    """
    cursor.execute(update_sql, (idle_json_str, machine_no))

    conn_mysql.commit()
    conn_mysql.close()

    print(f"ideal_time updated only for machine_no = {machine_no}")


# ---------- read from SQLite + update MySQL (running_time) ----------
def update_running_time_for_one_machine(sqlite_db_path, machine_no):
    conn_sqlite = sqlite3.connect(sqlite_db_path)
    cur_sqlite = conn_sqlite.cursor()

    query = """
        SELECT
            roll_id,
            start_time,
            end_time
        FROM start_timing_table
        WHERE machine_number = ?
        ORDER BY roll_id;
    """
    cur_sqlite.execute(query, (machine_no,))

    running_list = []

    rows = cur_sqlite.fetchall()
    for roll_id, start_str, end_str in rows:
        if not start_str or not end_str:
            continue

        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        end_dt   = datetime.strptime(end_str,   "%Y-%m-%d %H:%M:%S")

        diff_seconds = (end_dt - start_dt).total_seconds()
        if diff_seconds < 0:
            continue

        diff_seconds = int(diff_seconds)
        hrs = diff_seconds // 3600
        mins = (diff_seconds % 3600) // 60
        secs = diff_seconds % 60

        running_list.append({
            "roll_id": roll_id,
            "running_time": f"{hrs:02d}:{mins:02d}:{secs:02d}"
        })

    conn_sqlite.close()

    running_json_str = json.dumps(running_list)

    conn_mysql = get_mysql_connection()
    cursor = conn_mysql.cursor()

    update_sql = """
        UPDATE machine_performence
        SET running_time = %s
        WHERE machine_no = %s
    """
    cursor.execute(update_sql, (running_json_str, machine_no))

    conn_mysql.commit()
    cursor.close()
    conn_mysql.close()

    print(f"running_time updated only for machine_no = {machine_no}")

# ---------- read defects from SQLite + write into datas JSON in MySQL ----------
def update_defect_logs_for_one_machine(sqlite_db_path, machine_no):
    conn = sqlite3.connect(sqlite_db_path)
    cur = conn.cursor()

    query = """
    SELECT roll_id, defect_type
    FROM defect_logs
    WHERE machine_number = ?
    ORDER BY roll_id
    """
    cur.execute(query, (machine_no,))

    allowed_defects = ["hole", "needle_line", "oil", "double_yarn"]
    defect_map = {}   # roll_id (int) -> { "hole": int, "needle_line": int, "oil": int, "double_yarn": int }

    for roll_id, defect_type in cur.fetchall():
        if not defect_type:
            continue

        defect_type_raw = defect_type.lower().strip()

        # Ignore flups
        if "flups" in defect_type_raw:
            continue

        # Normalize defect names
        if "needle" in defect_type_raw:
            norm = "needle_line"
        elif "double" in defect_type_raw:
            norm = "double_yarn"
        elif "hole" in defect_type_raw:
            norm = "hole"
        elif "oil" in defect_type_raw:
            norm = "oil"
        else:
            # unknown defect -> skip
            continue

        # Ensure roll_id is int
        r_id = int(roll_id)

        # Initialize all 4 keys with 0 for this roll_id if not created yet
        if r_id not in defect_map:
            defect_map[r_id] = {k: 0 for k in allowed_defects}

        # Increase count for this defect type
        defect_map[r_id][norm] += 1

    conn.close()

    # Build final defect_logs list
    defect_logs = []
    for r_id, counts in defect_map.items():
        defect_logs.append({
            "roll_id": r_id,
            "defect_type": counts   # dict with 4 keys
        })

    # ---------- write into MySQL datas JSON ----------
    mysql_conn = get_mysql_connection()
    cur = mysql_conn.cursor()

    cur.execute("SELECT datas FROM machine_performence WHERE machine_no=%s", (machine_no,))
    row = cur.fetchone()

    base_json = {}
    if row and row[0]:
        try:
            base_json = json.loads(row[0])
        except json.JSONDecodeError:
            base_json = {}

    # keep same path: datas -> defect_logs
    base_json["defect_logs"] = defect_logs

    update_sql = """
    UPDATE machine_performence
    SET datas = %s
    WHERE machine_no = %s
    """

    cur.execute(update_sql, (json.dumps(base_json), machine_no))
    mysql_conn.commit()
    mysql_conn.close()

    print(f"✅ Defect logs (with counts) updated for machine {machine_no}")


# ---------- read start_timeing from SQLite + write into datas JSON in MySQL ----------
def update_start_timing_table_for_one_machine(sqlite_db_path, machine_no):
    
    conn_sqlite = sqlite3.connect(sqlite_db_path)
    cur_sqlite = conn_sqlite.cursor()

    query = """
        SELECT
            id,
            roll_id,
            start_time,
            end_time,
            machine_number,
            roll_seq
        FROM start_timing_table
        WHERE machine_number = ?
        ORDER BY id;
    """
    cur_sqlite.execute(query, (machine_no,))
    rows = cur_sqlite.fetchall()
    conn_sqlite.close()

    start_list = []
    for (
        row_id,
        roll_id,
        start_time,
        end_time,
        machine_number,
        roll_seq,
    ) in rows:
        start_list.append({
            "id": row_id,
            "roll_id": roll_id,
            "start_time": start_time,
            "end_time": end_time,
            "machine_number": str(machine_number) if machine_number is not None else None,
            "roll_seq": roll_seq,
        })

    # --------- 2) Read existing datas JSON from MySQL ----------
    mysql_conn = get_mysql_connection()
    cur_mysql = mysql_conn.cursor()

    cur_mysql.execute(
        "SELECT datas FROM machine_performence WHERE machine_no = %s",
        (machine_no,),
    )
    row = cur_mysql.fetchone()

    base_json = {}
    if row and row[0]:
        try:
            base_json = json.loads(row[0])
        except json.JSONDecodeError:
            base_json = {}

    # Get or create machine_performence object
    mp = (
        base_json.get("machine_performence")
        or base_json.get("machine_performance")
        or {}
    )

    mp["start_timing_table"] = start_list

    base_json["machine_performence"] = mp

    # --------- 3) Update MySQL ----------
    update_sql = """
        UPDATE machine_performence
        SET datas = %s
        WHERE machine_no = %s
    """

    cur_mysql.execute(update_sql, (json.dumps(base_json), machine_no))
    mysql_conn.commit()

    cur_mysql.close()
    mysql_conn.close()

    print(f"✅ start_timing_table updated for machine_no = {machine_no} (WITHOUT total_rotation)")


if __name__ == "__main__":
    SQLITE_DB = r"defect_database.db"

    # update_ideal_time_for_one_machine(SQLITE_DB, 5)
    # update_running_time_for_one_machine(SQLITE_DB, 6)
    #update_defect_logs_for_one_machine(SQLITE_DB, 6)
    #update_start_timing_table_for_one_machine(SQLITE_DB, 6)
