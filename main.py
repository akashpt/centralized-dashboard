from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import sqlite3

# ✅ IMPORT ALL DB HELPERS AT TOP (no need to import inside routes now)
from get_mysql import (
    get_db_data,
    get_db_machines,
    get_db_all_start_data,
    get_db_all_machine_performance,
)

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/machines")
def machines():
    return render_template("machines.html", content=get_db_machines())


@app.route("/machine_data/<string:value>")
def machine_data(value):
    return render_template("home.html", content=get_db_data(value))

@app.route("/report", methods=["GET"])
def report_page():
    
    machines = get_db_machines()
    machine_param = request.args.get("machine_no") 

    # default: first machine in list
    if machine_param is None and machines:
        machine_param = str(machines[0]["machine_no"])

    if machine_param == "ALL":
        # Overall report for ALL machines
        content = get_db_all_start_data()
        selected_machine = "ALL"
    else:
        # 👇 CHANGED: directly use the string (no int())
        content = get_db_data(machine_param) or {}
        selected_machine = machine_param

    return render_template(
        "report_file.html",
        content=content,
        machines=machines,
        selected_machine=selected_machine,
    )

@app.route("/machine_performance", methods=["GET"])
def machine_performance():

    machines = get_db_machines()
    machine_param = request.args.get("machine_no")  # '30EO' or 'ALL'

    # default: first machine
    if machine_param is None and machines:
        machine_param = str(machines[0]["machine_no"])

    if machine_param == "ALL":
        content = get_db_all_machine_performance()
        selected_machine = "ALL"
    else:
        # 👇 CHANGED: NO int() conversion
        content = get_db_data(machine_param) or {}
        selected_machine = machine_param

    return render_template(
        "machine_performance.html",
        content=content,
        machines=machines,
        selected_machine=selected_machine,
    )

@app.route("/api/get_data", methods=["GET"])
def get_data():
    # (same as your existing)
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    roll_id = request.args.get("roll")
    defect = request.args.get("type")

    response = {
        "received_filters": {
            "start_date": start_date,
            "end_date": end_date,
            "roll_id": roll_id,
            "defect_type": defect,
        },
        "message": "Filters received successfully ✅",
    }
    return jsonify(response) 


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)

