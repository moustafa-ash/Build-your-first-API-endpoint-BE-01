# Minimal FastAPI Backend

A lightweight, minimal backend server featuring two JSON endpoints. Built as the introductory assignment for the Backend AI Engineering track.

## Overview

This project demonstrates the fundamental request-response loop by standing up a local web server using FastAPI and Uvicorn. The server listens for GET requests and returns serialized JSON payloads, representing the basic building blocks for webhooks and API architectures.

## Tech Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python)
* **Server:** [Uvicorn](https://www.uvicorn.org/) (ASGI)

## Endpoints

| Method | Route | Description | JSON Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Root endpoint verifying server uptime. | `{"status":"success","message":"API is live."}` |
| `GET` | `/health` | Standard health check route. | `{"status":"healthy","system":"operational"}` |

## Local Development

### Prerequisites

Ensure Python is installed. Clone the repository, navigate to the project directory, and install the required dependencies using the text file:

```bash
pip install -r requirements.txt
```

### Running the Server

Launch the development server with live-reloading:

```bash
uvicorn main:app --reload

```

### Curl Outputs

```text
StatusCode        : 200
StatusDescription : OK
Content           : {"status":"success","message":"API is live."}
RawContent        : HTTP/1.1 200 OK
                    Content-Length: 45
                    Content-Type: application/json
                    Date: Sun, 12 Jul 2026 21:03:28 GMT
                    Server: uvicorn
                    
                    {"status":"success","message":"API is live."}
Forms             : {}
Headers           : {[Content-Length, 45], [Content-Type, application/json], [Date, Sun, 12 Jul 2026 21:03:28 GMT], [Server, uvicorn]}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        : mshtml.HTMLDocumentClass
RawContentLength  : 45

StatusCode        : 200
StatusDescription : OK
Content           : {"status":"healthy","system":"operational"}
RawContent        : HTTP/1.1 200 OK
                    Content-Length: 43
                    Content-Type: application/json
                    Date: Sun, 12 Jul 2026 21:03:00 GMT
                    Server: uvicorn
                    
                    {"status":"healthy","system":"operational"}
Forms             : {}
Headers           : {[Content-Length, 43], [Content-Type, application/json], [Date, Sun, 12 Jul 2026 21:03:00 GMT], [Server, uvicorn]}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        : mshtml.HTMLDocumentClass
RawContentLength  : 43

```
