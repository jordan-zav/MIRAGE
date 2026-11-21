# Publicación por el autor

Esta preparación es local. No se publicaron paquetes, tags ni releases. La distribución es mirage-geo y el paquete importable es mirage. Los pesos quedan fuera.

1. Revisa la rama feature/paquete-y-rutas, el informe de validación, licencias y artefactos; aprueba e integra a main. Antes de publicar configura los pasos siguientes: el push del tag inicia automáticamente el workflow.
2. En GitHub puedes configurar el entorno pypi restringido a tags v*. Si no existe, GitHub lo crea al primer uso.
3. En tu cuenta PyPI existente registra un Trusted Publisher para el proyecto mirage-geo: propietario jordan-zav, repositorio MIRAGE, archivo publish.yml, entorno pypi. Si el proyecto todavía no existe, usa un publicador pendiente desde la configuración de la cuenta; no necesitas un token ni una subida inicial manual.
4. Por decisión del autor no se usa TestPyPI: la publicación va directamente a PyPI.
5. Comprueba las versiones y crea/publica el tag inmutable de la version (por ejemplo v1.4.0) sobre el commit aprobado. El workflow publish.yml se dispara únicamente por push de tags v*, valida coincidencia de versión, Ruff, pytest, build, Twine y contenido. Conserva los logs del CI real; aquí solo se validó localmente.
6. El workflow construye una vez y envía los mismos wheel/sdist directamente a PyPI mediante OIDC y permisos id-token: write solo en el job de publicación. No usa secretos de API. Si falla, corrige el problema sin sobrescribir versiones ya publicadas; no uses skip-existing para ocultarlo.
7. Publica el release GitHub con las notas revisadas, ZIP QGIS y los artefactos realmente publicados con sus hashes. La publicación en el catálogo QGIS es un trámite separado.
8. Conecta/revisa Zenodo, archiva el release y añade el DOI real a CITATION.cff y .zenodo.json; no reserves ni inventes un DOI en el texto. Conserva el tag publicado inmutable; cualquier corrección se hace en un commit posterior.
9. Verifica la instalación por el tag público y por PyPI en entornos limpios. Comunica a TerraWorkbench que puede activar su pin de la nueva version solo cuando el tag esté publicado y comprobado.

La configuración remota de publicadores, entornos y disponibilidad del nombre no se comprobó ni modificó durante esta preparación. El workflow no tiene disparador manual, por rama ni por release.

Referencias oficiales: [guía PyPA de GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/), [publicador de proyecto nuevo](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) y [publicador existente](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).
