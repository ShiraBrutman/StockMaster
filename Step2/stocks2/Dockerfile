FROM python:3.11.7-slim

# Set the working directory in the container
WORKDIR /stocks2

# Copy requirements.txt and install dependencies
COPY app.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV FLASK_APP=app.py
ENV FLASK_RUN_PORT=8000
ENV NINJA_API_KEY='RMRgIp4laaBoVSyyoEg3oQ==kpRILqdNoYvzkjzX'
ENV MONGO_URI='mongodb://db:27017'

# Expose the port app runs on
EXPOSE 8000

# Command to run the app
CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]
