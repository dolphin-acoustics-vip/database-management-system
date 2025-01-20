from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

@app.route('/')
def maintenance_page():
    return "The OCEAN server is currently undergoing routine maintenance. Please come back later or contact your administrator for more information."

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('maintenance_page'))


if __name__ == '__main__':
    app.run(port=5000)