FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY pyproject.toml ./pyproject.toml
COPY . .
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt && python -m pip install .
ENTRYPOINT ["bash", "scripts/entrypoint.sh"]
