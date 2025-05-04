# Use an official Python runtime as the base image
FROM python:3.11

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY ./payment_service/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the command to run the payment_service app
CMD python utils/other/hotreload.py "payment_service/src/app.py"
