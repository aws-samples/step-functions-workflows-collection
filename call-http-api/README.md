# The "Call HTTP API" pattern

Make an HTTP/HTTPS request to an exteranl API and return the response.

![Call HTTP API diagram](./images/call-http-api.svg)

The workflow takes an Axios (Node.js-based HTTP client) config as input. For example,

```
# Step function input
{
	"config": {
		"url": "https://www.example.com",
		"method": "get"
		// More options can be found in https://axios-http.com/docs/req_config
	},
	"enableLog": true // Enable/disable Lambda logging.
  "forceIPv4": true // Currently Lambda functions do not support outbound IPv6. Default: true
}
```
(Remember to remove the comments before copy-pasting, they are not valid JSON)

You can see the full list of options in the [Axios documentation](https://axios-http.com/docs/req_config)

It returns the HTTP status code, header and response body in the `Payload` object:

```
# Step function input
{
	"Payload": {
		"status": 200
		"headers": {
			"content-type": "application/json"
			// ...
		},
		"response": {
			// HTTP response body
		}
	},
	// ...
}
```

# Deployment
```
sam build
sam deploy --guided
```

# Troubleshooting
* Error: `Runtime.ImportModuleError: Error: Cannot find module 'axios'`
  Solution: Run `sam build`, the run `sam deploy --guided` again.
