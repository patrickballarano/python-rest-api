#!/usr/bin/env python
import os
import json
import logging
import urllib.parse as urlparse
from flask import Flask, request, jsonify, Response
from flasgger import swag_from, Swagger
import time
import socket
import re
import validators
import psycopg2
from psycopg2.extras import DictCursor
from prometheus_client import Counter, generate_latest
from pathlib import Path

# read in version file
cwd = Path.cwd()
mod_path = Path(__file__).parent
rel_path = "../../VERSION"
VERSIONFILE = (mod_path / rel_path).resolve()
try:
    app_version = open(VERSIONFILE, "rt").read()
except EnvironmentError:
    pass


# initialize logging to file
logging.basicConfig(filename="access.log", level=logging.DEBUG)

app = Flask(__name__)

swagger_config = Swagger.DEFAULT_CONFIG
swagger_config[
    "swagger_ui_bundle_js"
] = "//unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js"
swagger_config[
    "swagger_ui_standalone_preset_js"
] = "//unpkg.com/swagger-ui-dist@3/swagger-ui-standalone-preset.js"
swagger_config["jquery_js"] = "//unpkg.com/jquery@2.2.4/dist/jquery.min.js"
swagger_config["swagger_ui_css"] = "//unpkg.com/swagger-ui-dist@3/swagger-ui.css"
swag = Swagger(app, config=swagger_config, template_file="swagger.json")


# Connect to db
def get_db_connection():
    """Return db connection"""
    url = urlparse.urlparse(os.environ["DATABASE_URL"])
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port

    conn = psycopg2.connect(
        dbname=dbname, user=user, password=password, host=host, port=port
    )
    return conn


def get_history():
    """Return history of last 20 requests from db"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    query_sql = "SELECT * FROM history ORDER BY id DESC LIMIT 20"
    cur.execute(query_sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # return rows
    all_rows = []
    for r in rows:
        all_rows.append(
            {
                "id": r["id"],
                "route": r["route"],
                "method": r["method"],
                "domain": r["domain"],
                "req_body": r["req_body"],
                "res_code": r["res_code"],
                "res_body": r["res_body"],
                "created_at": r["created_at"],
            }
        )

    return all_rows


# Prometheus Metrics
CONTENT_TYPE_LATEST = str("text/plain; version=0.0.4; charset=utf-8")
hit_counter = Counter(
    "hit_counter", "A url request hit counter.", ["method", "endpoint"]
)


# check k8s
def isk8s():
    """Returns True if running in k8s"""
    try:
        if "KUBERNETES_SERVICE_HOST" in os.environ:
            return True
        else:
            return False
    except:
        return False


# root endpoint returns unix epoch and version
@app.route("/", methods=["GET"])
def index():
    """Returns the unix epoch, version, and isK8s"""
    hit_counter.labels(request.method, request.endpoint).inc()
    return (
        jsonify(
            {"date": int(time.time()), "version": app_version, "kubernetes": isk8s()}
        ),
        200,
    )


@app.route("/metrics", methods=["GET"])
def metrics():
    """Returns all data as plaintext"""
    hit_counter.labels(request.method, request.endpoint).inc()
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# health endpoint returns 200
@app.route("/health", methods=["GET"])
def health():
    """Returns app health"""
    # not sure if enough to just return 200
    hit_counter.labels(request.method, request.endpoint).inc()
    return jsonify({"status": "ok"}), 200


# return ip address from hostname
@app.route("/v1/tools/lookup", methods=["GET"])
@swag_from("swagger.yaml")
# Note: Not sure if wanting domain lookup or ns lookup via dns tooling
def lookup():
    """Returns ipv4 address from domain name"""
    try:
        hit_counter.labels(request.method, request.endpoint).inc()
        domain = request.args.get("domain")
        hostname = socket.getfqdn(domain)
        req_body = request.query_string.decode()
        # validate domain
        if validators.domain(hostname):
            ip = []
            ip.append(socket.gethostbyname(hostname))
            resp = {
                "addresses": ip,
                "domain": hostname,
                "client_ip": request.remote_addr,
                "created_at": int(time.time()),
            }

            # Insert to db
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO history (route, method, domain, req_body, res_code, res_body) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    request.path,
                    request.method,
                    domain,
                    req_body,
                    jsonify(resp).status_code,
                    json.dumps(resp),
                ),
            )
            conn.commit()
            cur.close()
            conn.close()

            return resp, 200
        else:
            return (
                jsonify(
                    {
                        "message": "Not Found",
                    }
                ),
                404,
            )
    except Exception as e:
        print(e)
        return (
            jsonify(
                {
                    "message": "Bad Request",
                }
            ),
            400,
        )


# history queries
@app.route("/v1/history", methods=["GET"])
@swag_from("swagger.yaml")
def history():
    """Returns history of requests"""
    try:
        hit_counter.labels(request.method, request.endpoint).inc()
        rows = get_history()
        if rows:
            return jsonify(rows), 200
        else:
            return (
                jsonify(
                    {
                        "message": "No Records Found",
                    }
                ),
                404,
            )
    except:
        return (
            jsonify(
                {
                    "message": "Bad Request",
                }
            ),
            400,
        )


# return if input is ipv4 address
@app.route("/v1/tools/validate", methods=["POST"])
@swag_from("swagger.yaml")
def validate():
    # regex to validate ipv4 address
    """Returns validation of ipv4 address"""
    try:
        hit_counter.labels(request.method, request.endpoint).inc()
        data = request.get_json()
        ip = data["ip"]
        # regex
        regex = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        if re.search(regex, ip):
            return (
                jsonify(
                    {
                        "status": "true",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "status": "false",
                    }
                ),
                200,
            )
    except:
        return (
            jsonify(
                {
                    "message": "Bad Request",
                }
            ),
            400,
        )


if __name__ == "__main__":
    app.run("0.0.0.0", port=3000)
