#!/bin/bash
set -e

echo "🚀 Iniciando despliegue en Render..."

# 1. Aplicar migraciones (Crear tablas si no existen)
echo "🗄️ Aplicando migraciones de base de datos..."
flask db upgrade

# 2. Seed inicial si la BD está vacía
echo "🌱 Ejecutando seed (opcional)..."
rosemary db:seed

# 3. Arrancar Gunicorn
echo "🔥 Arrancando Gunicorn..."
gunicorn -w 1 --threads 4 --timeout 60 -b 0.0.0.0:5000 app:app
