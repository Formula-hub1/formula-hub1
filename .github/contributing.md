# 🤝 Guía de Contribución para FormulaHub

¡Gracias por tu interés en contribuir a FormulaHub! Tu ayuda es muy valiosa. Para mantener la calidad y la coherencia del proyecto, por favor, sigue estas directrices de flujo de trabajo y configuración.

## 🚀 Flujo de Trabajo

1.  **Issue:** Crea un Issue para discutir tu característica o corrección antes de empezar, usando las plantillas adecuadas.
2.  **Fork & Clone:** Haz un "fork" del repositorio y clona tu copia local.
3.  **Configuración Local:** Sigue la sección de "Configuración Obligatoria" a continuación para configurar tus hooks.
4.  **Desarrollo:** Implementa tus cambios.
5.  **Commit:** Usa mensajes de commit que sigan la convención.
6.  **Pull Request (PR):** Envía un PR a la rama `main` de FormulaHub, completando la plantilla correspondiente.

---

## 🛠️ Configuración Local Obligatoria

Es **esencial** que instales y actives los **hooks de Git** para asegurar que el código está formateado y los mensajes de commit son coherentes.

### 1. Requisitos

Asegúrate de tener instalado Python y Git en tu sistema.

### 2. Instalar la Herramienta `pre-commit`

Necesitas `pip` (Python) para instalar el gestor de hooks:

```bash
pip install pre-commit
```
### 3. Configurar la Plantilla de Mensaje de Commit

Configura Git para usar la plantilla `.gitmessage`. Esto precargará el formato al hacer `git commit`:

```bash
git config --local commit.template .gitmessage
```

### 4. Activar los Hooks de Git (Doble Instalación)

Debido a que usamos hooks para revisar archivos (etapa `pre-commit`) y hooks para revisar el mensaje (etapa `commit-msg`), debes ejecutar dos comandos de instalación para evitar duplicaciones:

# PASO A: Instala los hooks de código (Black, Flake8, etc.)
`pre-commit install`

# PASO B: Instala el hook validador de mensajes de commit
`pre-commit install --hook-type commit-msg`

## 📥 Pull Requests (PR)

* **Descripción:** Completa **TODOS** los campos de la plantilla **PULL_REQUEST_TEMPLATE.md** que se cargará automáticamente.
* **Tests:** Asegúrate de que todas las pruebas unitarias pasen.
* **Vínculo:** Si tu PR resuelve un Issue, inclúyelo en la descripción (ej: `Closes #123`).

## 🐛 Issues (Problemas)

Utiliza siempre las plantillas proporcionadas en la pestaña "Issues" de GitHub. Sé claro y conciso en tu reporte.
