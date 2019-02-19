import os
import json
from flask import Flask
import boto3
from werkzeug.utils import secure_filename
from flask import request
import tempfile


def create_app():
    app = Flask(__name__)

    services = json.loads(os.getenv("VCAP_SERVICES"))
    host = services["predix-blobstore"][0]["credentials"]["host"]
    if "https://" not in host:
        host = "https://" + host
    credentials = services["predix-blobstore"][0]["credentials"]
    access_key_id = credentials["access_key_id"]
    secret_access_key = credentials["secret_access_key"]
    bucket_name = credentials["bucket_name"]

    session = boto3.session.Session(
        aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key
    )

    config = boto3.session.Config(
        signature_version="s3",
        s3={"addressing_style": "virtual"},
        max_pool_connections=10000,
    )

    client = session.client("s3", endpoint_url=host, config=config)

    @app.route("/", methods=["POST"])
    def upload_files():
        logs = []
        for file in request.files.getlist("files[]"):
            with tempfile.NamedTemporaryFile(prefix="upload_", dir="/tmp") as tmpfile:
                file.save(tmpfile.name)
                filename = secure_filename(file.filename)
                logs.append(
                    client.upload_file(
                        tmpfile.name,
                        bucket_name,
                        filename,
                        ExtraArgs={"ServerSideEncryption": "AES256"},
                    )
                )
        return " ".join(str(x) for x in logs), 200

    return app
