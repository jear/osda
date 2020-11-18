
import json
import requests
import sys
import os

if len(sys.argv) <= 1 or len(sys.argv) > 2:
   print("#########################") 
   print("# ")
   print("# Usage: deploy-os.py <osda_json_file> ")
   print("# ")
   print("#########################") 
   sys.exit(0)

deployFile = sys.argv[1]

if not os.path.isfile(deployFile):
   print("\nInput file '{inputFile}' is not present\n".format(inputFile=deployFile))
   sys.exit(0)

url = 'http://10.188.210.205:5000/rest/deploy'
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

with open(deployFile, 'r') as fin:
    deployJSON = json.load(fin)

print("################################")
print(deployJSON)
print("################################")

x = requests.post(url, data = json.dumps(deployJSON), headers = headers)
print(x.text)
