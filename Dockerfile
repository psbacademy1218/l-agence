# Image autonome de "L'agence" — déployable sur n'importe quel hébergeur Docker
# (Render, Railway, Fly.io, un VPS…). Aucune dépendance externe à compiler.
FROM python:3.11-slim

WORKDIR /app
COPY . .

# La plateforme d'hébergement fixe PORT ; le serveur bind alors 0.0.0.0:$PORT.
ENV PORT=7000
EXPOSE 7000

CMD ["python", "agency.py", "dashboard"]
