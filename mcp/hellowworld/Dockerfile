FROM python:3.11-slim
WORKDIR /app
RUN pip install mcp fastmcp uvicorn
COPY server.py .
EXPOSE 8080
CMD ["python", "server.py"]
