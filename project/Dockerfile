FROM python:3.8

EXPOSE 3111/tcp

WORKDIR /app

COPY techtrends/requirements.txt /app
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY techtrends/ /app
RUN python init_db.py

CMD ["python", "app.py"]
