# Nginx Docker Setup (The \"Greeter\")

This directory contains the Nginx configuration needed to catch traffic coming into your Azure VM on ports 80 and 443.

## How it works

1. Your Azure VM allows traffic on ports 80 (HTTP) and 443 (HTTPS) through the Network Security Group (NSG) firewall.
2. The Docker daemon maps the VM's ports 80 and 443 to the Nginx container (as defined in `docker-compose.prod.yml`).
3. Nginx (the "Greeter") receives the incoming requests.
4. Nginx then reads `nginx.conf` and forwards the traffic to the `backend` container on port 8000 using Docker's internal network.

## Next Steps

Right now, `nginx.conf` is configured to listen on port 80 and route traffic to the backend over HTTP.

**To run the production setup with Nginx:**
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### Setting up SSL (HTTPS)

Once you have pointed your domain name to the Azure VM's IP address:
1. Obtain an SSL certificate (e.g., using Certbot/Let's Encrypt).
2. Place the certificate (`fullchain.pem`) and private key (`privkey.pem`) into the `nginx/ssl` folder on the VM.
3. Edit `nginx/nginx.conf`:
   - Uncomment the `return 301 https://$host$request_uri;` line in the expected HTTP server block.
   - Uncomment the entire HTTPS server block (listen 443 ssl) and change `yourdomain.com` to your actual domain.
4. Restart Nginx: `docker-compose -f docker-compose.prod.yml restart nginx`
