from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.hosts import add_host, get_host, init_db, list_hosts, remove_host
from services.network import detect_interface
from services.shell import run
from services.validation import validate_host

SSH_KEY = Path("private/wakelet")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

init_db()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"hosts": list_hosts()})


@app.post("/hosts", response_class=HTMLResponse)
def create_host(request: Request, name: str = Form(...), mac: str = Form(...)):
    errors = validate_host(name, mac)
    if errors:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"hosts": list_hosts(), "errors": errors, "form": {"name": name, "mac": mac}},
            status_code=422,
        )
    add_host(name, mac)
    return RedirectResponse("/", status_code=303)


@app.post("/hosts/{host_id}/remove")
def delete_host(host_id: int):
    remove_host(host_id)
    return RedirectResponse("/", status_code=303)


@app.post("/hosts/{host_id}/wake", response_class=HTMLResponse)
async def wake_host(host_id: int, request: Request):
    host = get_host(host_id)
    command = ["sudo", "etherwake", "-b", "-D", "-i", detect_interface(), host.mac]
    result = await run(command)
    return templates.TemplateResponse(
        request,
        "command_result.html",
        {"command": " ".join(command), "result": result},
    )


@app.post("/hosts/{host_id}/shutdown", response_class=HTMLResponse)
async def shutdown_host(host_id: int, request: Request):
    host = get_host(host_id)
    command = [
        "ssh",
        "-i", str(SSH_KEY),
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        f"wakelet@{host.name}",
    ]
    result = await run(command)
    return templates.TemplateResponse(
        request,
        "command_result.html",
        {"command": " ".join(command), "result": result},
    )


@app.post("/hosts/{host_id}/ping", response_class=HTMLResponse)
async def ping_host(host_id: int, request: Request):
    host = get_host(host_id)
    command = ["ping", "-W1", "-c2", host.name]
    result = await run(command)
    return templates.TemplateResponse(
        request,
        "command_result.html",
        {"command": " ".join(command), "result": result},
    )


@app.get("/ping", response_class=HTMLResponse)
async def ping(request: Request):
    command = ["ping", "-w5", "-c4", "google.com"]
    result = await run(command)
    return templates.TemplateResponse(
        request,
        "command_result.html",
        {"command": " ".join(command), "result": result},
    )