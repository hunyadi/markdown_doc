ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-alpine
RUN python3 -m pip install --disable-pip-version-check --upgrade pip
COPY dist/*.whl dist/
RUN python3 -m pip install --disable-pip-version-check `ls -1 dist/*.whl`
COPY check.py /
COPY markdown_doc/ markdown_doc/
RUN python3 check.py
