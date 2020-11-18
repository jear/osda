# RESTful API Reference

The structure of the response for REST calls:

```
{
    result: {},
    error: {}
}
```





# Deployment using HPE OneView

## Register HPE OneView Appliance
Register HPE OneView appliance with the tool.

### Request: 
```
METHOD: POST
URL: /rest/oneview/add
HEADERS: {Content-Type: application/json}
BODY:
{
	"alias": "",
	"ipaddr": "",
	"username": "",
	"password": ""
}
```

Response:
```
{
  "error": {},
  "result": "success"
}
```
Possible values for the result string are:
"success",
"failed"

## Get list of registered HPE OneView Appliances
Gets the list of HPE OneView appliances registered with the tool.
### Request
```
METHOD: GET
URL:    /rest/oneview/list
HEADERS: {Content-Type: application/json}
```

### Response:
The response contains the list of connection settings for the OneView appliances registered with the tool.

```
{
    result:   [{
      "alias": "",
      "ipaddr": "",
      "ov_cert_path": "",
      "password": "",
      "username": ""
    },                
    ]
    error: {}
}
```

_Status: implemented and tested_

## Edit HPE OneView Appliance details

#### Edit OneView connection
`'/rest/oneview/del', methods=['POST'])`
>(TODO) Edits OneView connection


#### Delete OneView connection
`'/rest/oneview/del', methods=['POST'])`
>(TODO) Deletes OneView connection


#### List OneView Server Profile Templates
`'/rest/oneview/spt/list', methods=['GET'])`
>Gets the list of Server Profile Templates from the specified OneView appliance

#### List ethernet connections defined in OneView Server Profile Template
`'/rest/oneview/spt/connections?ovname=oneviewappliancename?spt=serverprofiletemplatename', methods=['GET'])`
>Get list of network connections defined in the the server profile template. 
The OneView appliance name and server profile template names are specified as query params in the URL.


#### List the storage drives from OneView Server Profile Template
`'/rest/oneview/spt/drives?spt=<SPT>?ovname=<OneView alias>', methods=['GET'])`
>Get the list of storage drives for the specified server profile template.
**Note:** *OneView 4.1 doesnt return local drive information from the SPT or SP. As a workaround the returned list is appended with hardcoded item with name localdrive*
The OneView appliance name and server profile template names are specified as query params in the URL.


### OS Packages
#### List supported Operating System Types
`'/rest/ostype/list', methods=['GET'])`
>Get the list of operating systems supported by the tool

#### Upload file
`'/rest/upload', methods=['POST'])`
>File upload. Supports ISO and CSV types.
Uses the body JSON content for determining further processing of the uploaded file.

#### List the OS Packages
`'/rest/ospackage/list', methods=['GET'])`
>Get the list of user created OS packages.

#### Get the OS Package by ID
`'/rest/ospackage/<id>', methods=['GET'])`
>Get the OS package details by ID

### Server deployment 
#### Deploy the server(s)
`'/rest/deploy', methods=['POST'])`
>Deploy the OS on the specified server(s)

#### Get the list of tasks
`'/rest/tasks', methods=['GET'])`
>Get list of the deployment tasks (including the completed tasks)

`'/rest/tasks/<int:taskid>', methods=['GET'])`
>Get the task details by ID. 

### Settings


