import os
import sys
import threading
import webbrowser
from flask import Flask, render_template, jsonify, request

# ================= RESOURCE PATH (PyInstaller FIX) =================
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ================= FLASK APP =================
app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static")
)

# ================= DB IMPORTS =================
from get_mysql import (
    get_db_data,
    get_db_machines,
    get_db_all_start_data,
    get_db_all_machine_performance,
)

# ================= ROUTES =================
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

    if machine_param is None and machines:
        machine_param = str(machines[0]["machine_no"])

    if machine_param == "ALL":
        content = get_db_all_start_data()
        selected_machine = "ALL"
    else:
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
    machine_param = request.args.get("machine_no")

    if machine_param is None and machines:
        machine_param = str(machines[0]["machine_no"])

    if machine_param == "ALL":
        content = get_db_all_machine_performance()
        selected_machine = "ALL"
    else:
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
    return jsonify({"status": "ok"})

# ================= AUTO OPEN BROWSER =================
def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

# ================= MAIN =================
if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)