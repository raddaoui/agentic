docker run -p 7777:8080  ghcr.io/raddaoui/mcp-server:v1
docker push ghcr.io/raddaoui/mcp-server:v1
docker tag mcp-inspector:latest ghcr.io/raddaoui/mcp-server:v1