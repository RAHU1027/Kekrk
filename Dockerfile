# Python ka halka aur fast version use kar rahe hain
FROM python:3.9-slim

# Bot ki files ko /app folder mein copy karo
WORKDIR /app
COPY . .

# Zaruri libraries install karo
RUN pip install --no-cache-dir -r requirements.txt

# Bot start karne ki command
CMD ["python", "bot.py"]
