
import json

import requests



url = 'http://10.188.210.14:5000/rest/deploy'

headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

fin = open('./deploy-ilo-hosts.json', 'r')

deployJSON = json.load(fin)

print("################################")
print(deployJSON)
print("################################")

x = requests.post(url, data = json.dumps(deployJSON), headers = headers)

print(x.text)
