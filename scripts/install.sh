#!/bin/bash

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Asegurar que estamos en la raíz del proyecto ---
cd "$(dirname "$0")/.."

echo -e "${GREEN}🚀 Iniciando instalación de FormulaHub...${NC}"

# --- PASO 0: Comprobar entorno virtual ---
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  ADVERTENCIA: No parece que tengas activado el entorno virtual.${NC}"
    echo "   Se recomienda ejecutar: source venv/bin/activate"
    read -p "   ¿Quieres continuar de todas formas? (s/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${RED}Cancelando instalación.${NC}"
        exit 1
    fi
fi

# --- PASO 1: Dependencias ---
echo -e "\n${GREEN}📦 Instalando dependencias...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error instalando requirements.txt.${NC}"
    exit 1
fi

pip install -e .

# --- PASO 2: Configuración (.env) ---
echo -e "\n${GREEN}⚙️  Configurando entorno...${NC}"
if [ ! -f .env ]; then
    # Intenta copiar el ejemplo local, si no existe, busca el ejemplo general
    if [ -f .env.local.example ]; then
        cp .env.local.example .env
    elif [ -f .env.example ]; then
        cp .env.example .env
    else
        echo -e "${YELLOW}⚠️  No se encontró .env.local.example ni .env.example.${NC}"
    fi
    echo "✅ Archivo .env creado."
else
    echo -e "${YELLOW}⚠️  El archivo .env ya existe, se mantiene el actual.${NC}"
fi

# --- PASO 3: Base de Datos ---
echo -e "\n${GREEN}🗄️  Inicializando base de datos...${NC}"

flask db upgrade
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo -e "\n${RED}❌ ERROR CRÍTICO: Falló la migración de la base de datos.${NC}"
    echo -e "${YELLOW}Posible solución: La base de datos no está creada o el usuario es incorrecto.${NC}"
    echo -e "Prueba a ejecutar estos comandos en tu cliente MySQL/MariaDB (como root):"

    echo -e "${BLUE}-------------------------------------------------------${NC}"
    echo -e "${BLUE}CREATE DATABASE IF NOT EXISTS uvlhubdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;${NC}"
    echo -e "${BLUE}CREATE USER IF NOT EXISTS 'uvlhubdb_user'@'localhost' IDENTIFIED BY 'uvlhubdb_password';${NC}"
    echo -e "${BLUE}GRANT ALL PRIVILEGES ON uvlhubdb.* TO 'uvlhubdb_user'@'localhost';${NC}"
    echo -e "${BLUE}FLUSH PRIVILEGES;${NC}"
    echo -e "${BLUE}-------------------------------------------------------${NC}"

    echo -e "(Datos basados en tu configuración por defecto)"
    exit 1
fi

echo -e "\n${GREEN}✅ Instalación completada con éxito.${NC}"
echo -e "🏁 Ejecuta ${YELLOW}flask run${NC} para iniciar el servidor."
