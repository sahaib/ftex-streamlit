# Docker Deployment

## Quick Start

```bash
git clone https://github.com/sahaib/ftex-streamlit.git
cd ftex-streamlit
docker-compose up -d
```

## With Local AI (Ollama)

```bash
docker-compose --profile ai up -d
docker exec ftex-ollama ollama pull qwen2.5:14b
```

## Production Setup

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name ftex.example.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### With SSL

```bash
certbot --nginx -d ftex.example.com
```
