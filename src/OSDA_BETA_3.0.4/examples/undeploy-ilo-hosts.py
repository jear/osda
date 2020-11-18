
import json

import requests



url = 'http://10.188.175.100:5000/rest/undeploy'

headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

fin = open('./sample_delete_host.json', 'r')

deployJSON = json.load(fin)

print("################################")
print(deployJSON)
print("################################")

x = requests.delete(url, data = json.dumps(deployJSON), headers = headers)

print(x.text)
