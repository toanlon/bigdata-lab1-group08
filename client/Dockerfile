ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}

ARG BOTO3_VERSION
RUN pip install --no-cache-dir "boto3==${BOTO3_VERSION}"

COPY s3lab.py /opt/s3lab.py

CMD ["sleep", "infinity"]
