from datetime import datetime
import json
import uuid
from classes.live_data import fetch_live_machines,get_user
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot


# class CameraWorker(QObject):
#     frame_ready = pyqtSignal(str)
#     finished = pyqtSignal()

#     def __init__(self):
#         super().__init__()
#         self.running = False

#     @pyqtSlot()
#     def run(self):
#         cap = cv2.VideoCapture(0)
#         self.running = True
#         while self.running:
#             ret, frame = cap.read()
#             if ret:
#                 _, buf = cv2.imencode(".jpg", frame)
#                 self.frame_ready.emit(base64.b64encode(buf).decode())
#         cap.release()
#         self.finished.emit()

#     def stop(self):
#         self.running = False


class Bridge(QObject):
    sessionEnded = pyqtSignal()

    def __init__(self, app_ref=None):
        super().__init__()
        self.app_ref = app_ref
        self.cam_thread = None
        self.cam_worker = None
        self.cam_running = False
        self.material = ""
        self._uptime = 0
        self._inspected = 0
        self._defects = 0
        self._duff_count = 100
        self.session_id = str(uuid.uuid4())
        self._users = {
            "admin": {
                "password": "admin@123",
                "name": "Admin",
                "initials": "AD",
            }
        }

        self._timer = QTimer(self)
        self._timer.setInterval(1000)

       
    def _json(self, payload):
        return json.dumps(payload)

    def _machine_data(self):
        return fetch_live_machines()

    def _machine_id(self, machine):
        return f"machine-{machine.get('machine_no')}"

    def _machine_status(self, machine):
        status = str(machine.get("machine_status") or "").lower()
        if status == "running":
            return "running"
        return "stopped"

    def _data_machine_to_machine(self, machine):
        machine_no = str(machine.get("machine_no") or "")
        live_data = machine.get("live_datas") or {}
        return {
            "id": self._machine_id(machine),
            "no": machine_no,
            "name": f"Machine {machine_no}",
            "status": self._machine_status(machine),
            "image": "../static/img/machine_image.jpeg",
            "line": "",
            "operator": "",
            "location": "",
            "model": "",
            "serial": str(machine.get("id") or ""),
            "lastService": self._date_only(machine.get("updated_at")),
            "liveParameters": {
                "Material": live_data.get("material", ""),
                "Doff Number": live_data.get("doff_number", 0),
                "Inspected": live_data.get("inspect", 0),
                "Good": live_data.get("good", 0),
                "Defect": live_data.get("defect", 0),
                "Empty": live_data.get("empty", 0),
            },
        }

    def _date_only(self, value):
        if not value:
            return ""
        return str(value).split("T", 1)[0].split(" ", 1)[0]

    def _time_only(self, value):
        if not value:
            return ""
        return str(value).replace("T", " ").split(" ", 1)[-1].replace(".000Z", "")

    def _duration(self, start, end):
        try:
            start_dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        except ValueError:
            return ""

        seconds = int((end_dt - start_dt).total_seconds())
        if seconds < 0:
            return ""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    def _data_for_machine(self, machine_id):
        machines = self._machine_data()
        if not machines:
            return None

        return next(
            (machine for machine in machines if self._machine_id(machine) == machine_id),
            None,
        )

    def _defects_for_report(self, machine, report_data):
        defect_count = int(report_data.get("defect") or 0)
        if defect_count <= 0:
            return []

        doff_number = report_data.get("doff_number", machine.get("machine_no", 0))
        created_at = report_data.get("doff_start", "")
        end_time = report_data.get("doff_end", "")
        rows = []
        for index in range(min(defect_count, 8)):
            rows.append(
                {
                    "id": int(f"{machine.get('machine_no', 0)}{doff_number}{index + 1:02d}"),
                    "copNumber": (index + 1) * 4,
                    "thread": 72 + (index * 3),
                    "createdAt": created_at,
                    "endTime": end_time,
                    "result": "defect",
                }
            )
        return rows

    def _data_machine_to_report(self, machine):
        reports = machine.get("report_datas") or []
        live_data = machine.get("live_datas") or {}
        report_data = reports[0] if reports else live_data
        machine_no = str(machine.get("machine_no") or "")
        doff_start = report_data.get("doff_start", "")
        doff_end = report_data.get("doff_end", "")

        return {
            "frNo": f"FR-{report_data.get('doff_number', machine_no)}",
            "machineNo": machine_no,
            "date": self._date_only(doff_start or doff_end),
            "doffNo": report_data.get("doff_number", ""),
            "material": report_data.get("material", ""),
            "yarn": "",
            "count": "",
            "startTime": self._time_only(doff_start),
            "endTime": self._time_only(doff_end),
            "duration": self._duration(doff_start, doff_end),
            "stats": {
                "Total Cops": report_data.get("inspect", 0),
                "Defect Count": report_data.get("defect", 0),
                "Total Good Cops": report_data.get("good", 0),
                "Total Full Cops": report_data.get("full_cops", 0),
                "Total Half Cops": report_data.get("half_cops", 0),
                "Total Quarter Cops": report_data.get("quarter_cops", 0),
            },
            "defects": self._defects_for_report(machine, report_data),
        }

    @pyqtSlot(result=str)
    def getSessionId(self):
        return self.session_id

    @pyqtSlot(str, str, result=str)
    def authenticate(self, username, password):

        user = get_user(username.strip())

        if not user:
            return self._json({
                "ok": False,
                "error": "User not found"
            })

        if user["password"] != password:
            return self._json({
                "ok": False,
                "error": "Invalid password"
            })

        return self._json({
            "ok": True,
            "sessionId": self.session_id,
            "user": {
                "name": user["user_name"],
                "initials": user["user_name"][:2].upper(),
                "page_name": user["page_name"]
            }
        })

    @pyqtSlot(result=str)
    def getMachines(self):
        machines = self._machine_data()
        cards = [
            {
                "id": self._machine_id(machine),
                "no": str(machine.get("machine_no") or ""),
                "name": f"Machine {machine.get('machine_no')}",
                "status": self._machine_status(machine),
                "image": "../static/img/machine_image.jpeg",
            }
            for machine in machines
        ]
        return self._json({"ok": True, "machines": cards})

    @pyqtSlot(str, result=str)
    def getMachineDetails(self, machineId):
        machine = self._data_for_machine(machineId)
        if machine is None:
            return self._json({"ok": False, "error": "Machine not found"})

        return self._json(
            {
                "ok": True,
                "machine": self._data_machine_to_machine(machine),
                "report": self._data_machine_to_report(machine),
            }
        )

    @pyqtSlot(result=str)
    def getAllMachineDetails(self):
        machines = [
            {
                "machine": self._data_machine_to_machine(machine),
                "report": self._data_machine_to_report(machine),
            }
            for machine in self._machine_data()
        ]
        return self._json({"ok": True, "machines": machines})

    @pyqtSlot(str, result=str)
    def getReport(self, machineId):
        machine = self._data_for_machine(machineId)
        if machine is None:
            return self._json({"ok": False, "error": "Machine not found"})

        return self._json(
            {
                "ok": True,
                "machine": self._data_machine_to_machine(machine),
                "report": self._data_machine_to_report(machine),
            }
        )

    @pyqtSlot()
    def clearLoginSession(self):
        self.sessionEnded.emit()

    @pyqtSlot()
    def open_report_window(self):
        if self.app_ref and hasattr(self.app_ref, "open_report_window"):
            self.app_ref.open_report_window()

    @pyqtSlot()
    def goHome(self):
        self._go("index.html")

    @pyqtSlot()
    def goReport(self):
        self._go("report.html")

    @pyqtSlot()
    def goTraining(self):
        self._go("training.html")

    @pyqtSlot()
    def goController(self):
        self._go("controller.html")

    def _go(self, page_name):
        if self.app_ref and hasattr(self.app_ref, "load_page"):
            self.app_ref.load_page(page_name)

    # def stopCamera(self):
    #     if self.cam_worker:
    #         self.cam_worker.stop()
