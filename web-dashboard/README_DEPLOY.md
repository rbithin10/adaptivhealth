AdaptivHealth Web Dashboard — build & deploy
=========================================

This file explains how to build a production-ready static bundle of the React dashboard and deploy it so it can be accessed from anywhere.

Environment variable
- The frontend reads backend URL from `REACT_APP_API_URL` at build time. Set it to your backend (EC2, ALB, or local).

Quick local production test
--------------------------
1. Build:

```bash
cd web-dashboard
npm ci
npm run build
```

2. Serve the build locally (production-like):

```bash
npm run start-prod
# opens on http://localhost:5000
```

Deploy to EC2 using Docker (recommended for this project)
------------------------------------------------------
1. Build and run on EC2 (example):

```bash
# on your local machine
cd web-dashboard
docker build -t adaptiv-dashboard:latest .
docker save adaptiv-dashboard:latest | pv | ssh ec2-user@<EC2_IP> 'docker load'

# on EC2 (or build directly on the instance):
docker run -d -p 80:80 --name adaptiv-dashboard adaptiv-dashboard:latest
```

Now the dashboard will be served from http://<EC2_IP>. Ensure security group allows inbound HTTP/HTTPS.

Alternative deployment options
--------------------------------
- S3 + CloudFront: upload `build/` as a static site, configure CloudFront for HTTPS and custom domain.
- Vercel / Netlify: connect the repo and set `REACT_APP_API_URL` environment variable in the project settings; they’ll handle TLS and CDN.

Notes and recommendations
- For production, serve the frontend over HTTPS and point `REACT_APP_API_URL` to an HTTPS backend.
- Keep `REACT_APP_API_URL` set at build time; after building the app, the value is baked into the JS bundle.
- For easily switching between local and remote backends during development, use `.env.local` (gitignored) with `REACT_APP_API_URL=http://localhost:8080`.
