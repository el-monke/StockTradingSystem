from flask import Flask, render_template
from flask_bootstrap import Bootstrap5

app = Flask(__name__)
bootstrap = Bootstrap5(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/createaccount")
def createaccount():
    return render_template("createaccount.html")

if __name__ == "__main__":
    app.run(debug=True)