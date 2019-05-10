from flask import Flask
import subprocess
import re
from flask import json

app = Flask(__name__)

def countoverlappingdistinct(pattern, thestring):
  total = 0
  start = 0
  there = re.compile(pattern)
  while True:
    mo = there.search(thestring, start)
    if mo is None: return total
    total += 1
    start = 1 + mo.start()

@app.route("/getNConnected")
def hello():

    a = subprocess.run(["sh", "script.sh"], stdout=subprocess.PIPE)
    b = countoverlappingdistinct("([0-9a-fA-F]:?){12}", a.stdout.decode("utf-8"))
    c = '{"n": ' + str(b) + '}'

    response = app.response_class(
        response=json.dumps(c),
        status=200,
        mimetype='application/json'
    )
    
    return response
    