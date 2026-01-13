# PixelOTAGenerator
PixelOTAGenerator is a tool that automates the process of AVBRoot-ing Pixel OTA updates. It periodically checks for new OTA updates from the Android developer site, roots them with KernelSU(+SuSFS), and runs them through Custota for easy installation.
1. Obtain `avb.key`, `ota.key`, and `ota.crt` from your avbroot setup, and put them into a directory called `avbroot-input`
2. Make a new `docker-compose.yml` file with the following contents:
```yaml
services:
    pog:
        image: ghcr.io/blucobalt/pixelotagenerator:latest
        container_name: pog
        volumes:
          - ./avbroot-input:/app/avbroot-input
          - ./output:/app/output
        environment:
          # comma separated list of devices to generate OTAs for, e.g. "tokay,tangorpro"
          - POG_DEVICES=tokay,tangorpro
          # interval in hours between checking for new upstream OTAs
          - POG_INTERVAL_HOURS=12
        restart: unless-stopped
    webserver:
        image: caddy:latest
        container_name: webserver
        volumes:
          - ./output:/var/www/html
          - ./Caddyfile:/etc/caddy/Caddyfile:ro
        ports:
          - "5000:80"
        restart: unless-stopped
```
3. Create a `Caddyfile` with the following contents:
```
:80 {
    root * /var/www/html
    file_server browse
}
```
4. Now, run `docker-compose up -d` to start everything. Point custota to `caddy:5000` or some version of TLS termination proxy that points to `caddy:5000` and you are set!
