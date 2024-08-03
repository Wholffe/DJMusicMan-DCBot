from threading import Thread

from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "DJ Music Man is ready to jam."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_jamming():
    t = Thread(target=run)
    t.start()