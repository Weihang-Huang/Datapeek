FROM python:3.11-slim

WORKDIR /app

# Install system deps for HDF5, NetCDF, LMDB, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libhdf5-dev libnetcdf-dev liblmdb-dev gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web_app/ web_app/

EXPOSE 5000

ENV MAX_CONTENT_LENGTH=524288000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "web_app.app:app"]
