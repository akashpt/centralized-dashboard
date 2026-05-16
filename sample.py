import webbrowser
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello Flask!"

if __name__ == "__main__":
    url = "http://127.0.0.1:5000"
    webbrowser.open(url)  # <-- opens default browser
    app.run(host="127.0.0.1", port=5000, debug=False)
