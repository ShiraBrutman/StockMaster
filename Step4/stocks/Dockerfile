FROM python:3.11.7-slim
#FROM  invalid_image:1.0

# Set working directory in the container
WORKDIR /stocks

# Create logs directory
RUN mkdir -p /stocks/logs && chmod 777 /stocks/logs

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install gunicorn


COPY . .

ENV FLASK_APP=app.py
ENV FLASK_RUN_PORT=8000
ENV NINJA_API_KEY='RMRgIp4laaBoVSyyoEg3oQ==kpRILqdNoYvzkjzX'
ENV MONGO_URI='mongodb://db:27017'

# Expose the port app runs on
EXPOSE 8000

# Command to run the app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
