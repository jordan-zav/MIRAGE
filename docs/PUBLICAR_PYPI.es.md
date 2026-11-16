# Publicación por el autor

Esta preparación es local. No se publicaron paquetes, tags ni releases. La distribución es mirage-lineaments y el paquete importable es mirage. Los pesos quedan fuera.

1. Revisa la rama feature/paquete-y-rutas, el informe de validación, licencias y artefactos; aprueba e integra a main. Antes de publicar configura los pasos siguientes: el push del tag inicia automáticamente el workflow.
2. En GitHub configura los entornos testpypi y pypi. Protege pypi con aprobación del autor para revisar TestPyPI antes del paso definitivo; restringe ambos a tags v*. La disponibilidad de revisores depende del plan del repositorio.
3. En tu cuenta PyPI existente registra un Trusted Publisher para el proyecto mirage-lineaments: propietario jordan-zav, repositorio MIRAGE, archivo publish.yml, entorno pypi. Si el proyecto todavía no existe, usa un publicador pendiente desde la configuración de la cuenta; no necesitas un token ni una subida inicial manual.
4. Repite la configuración en TestPyPI con entorno testpypi. PyPI y TestPyPI son servicios separados; inicia sesión con una cuenta propia de TestPyPI si ya dispones de ella, o realiza personalmente su alta si hiciera falta. Esta tarea no crea cuentas ni tokens.
5. Comprueba las versiones y crea/publica el tag inmutable v1.3.0 sobre el commit aprobado. El workflow publish.yml se dispara únicamente por push de tags v*, valida coincidencia de versión, Ruff, pytest, build, Twine y contenido. Conserva los logs del CI real; aquí solo se validó localmente.
6. El workflow construye una vez y envía los mismos wheel/sdist primero a TestPyPI y después a PyPI mediante OIDC y permisos id-token: write solo en los jobs de publicación. No usa secretos de API. Revisa el proyecto de TestPyPI y los archivos antes de aprobar el entorno pypi. Si falla, corrige el problema sin sobrescribir versiones ya publicadas; no uses skip-existing para ocultarlo.
7. Publica el release GitHub con las notas revisadas, ZIP QGIS y los artefactos realmente publicados con sus hashes. La publicación en el catálogo QGIS es un trámite separado.
8. Conecta/revisa Zenodo, archiva el release y añade el DOI real a CITATION.cff y .zenodo.json; no reserves ni inventes un DOI en el texto. Conserva el tag publicado inmutable; cualquier corrección se hace en un commit posterior.
9. Verifica la instalación por el tag público y por PyPI en entornos limpios. Comunica a TerraWorkbench que puede activar su pin v1.3.0 solo cuando el tag esté publicado y comprobado.

La configuración remota de publicadores, entornos y disponibilidad del nombre no se comprobó ni modificó durante esta preparación. El workflow no tiene disparador manual, por rama ni por release.

Referencias oficiales: [guía PyPA de GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/), [publicador de proyecto nuevo](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) y [publicador existente](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).
