from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>✅ Flask Jalan!</h1><p>Dashboard monitoring beban trafo siap deploy.</p>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
