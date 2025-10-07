# Build and tag the image
docker build -t mcp-server:latest .

# Tag the image for GitHub Container Registry
docker tag mcp-server:latest ghcr.io/raddaoui/mcp-server:v1

# Push the image to the registry
docker push ghcr.io/raddaoui/mcp-server:v1

# Run the container locally
docker run -p 8080:8080 ghcr.io/raddaoui/mcp-server:v1
