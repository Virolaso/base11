"""API de proyectos: CRUD, versiones, exportes, descarga."""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse


def create_projects_router(*, jobs, sanitize_track_name, processed_dir: Optional[str] = None) -> APIRouter:
    """Router de gestión de proyectos con versiones y exportes.
    
    Endpoints:
      POST   /projects               → crear proyecto
      GET    /projects               → listar proyectos
      GET    /projects/{id}          → detalle de proyecto
      PUT    /projects/{id}          → actualizar metadatos
      POST   /projects/{id}/versions → crear versión (asocia job)
      GET    /projects/{id}/versions/{name} → detalle de versión
      POST   /projects/{id}/versions/{name}/exports → registrar exportes
      GET    /projects/{id}/versions/{name}/download/{export_id} → descargar
      DELETE /projects/{id}          → archivar proyecto
    """
    router = APIRouter()
    processed_dir = processed_dir or os.path.join(os.getcwd(), "processed")

    def _ensure_export_dir() -> str:
        os.makedirs(processed_dir, exist_ok=True)
        return processed_dir

    # ─────────────────────────────────────────────────────────────────
    # Proyectos: CRUD
    # ─────────────────────────────────────────────────────────────────

    @router.post("/projects", tags=["Projects"], response_model=dict)
    def create_project(title: str, artist: Optional[str] = None, metadata: Optional[dict] = None):
        """Crear un proyecto nuevo (contenedor de versiones/exportes)."""
        import uuid
        project_id = str(uuid.uuid4())[:8]
        payload = {
            "title": str(title),
            "artist": str(artist or "Unknown"),
            "status": "active",
        }
        if metadata:
            payload.update(metadata)
        return jobs.create_project(project_id, payload)

    @router.get("/projects", tags=["Projects"], response_model=dict)
    def list_projects():
        """Listar todos los proyectos."""
        return {"projects": [v for v in jobs.list_projects().values()]}

    @router.get("/projects/{project_id}", tags=["Projects"], response_model=dict)
    def get_project(project_id: str):
        """Obtener detalles de un proyecto."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        return project

    @router.put("/projects/{project_id}", tags=["Projects"], response_model=dict)
    def update_project(project_id: str, title: Optional[str] = None, artist: Optional[str] = None, status: Optional[str] = None):
        """Actualizar metadatos del proyecto."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        
        if title:
            project["title"] = str(title)
        if artist:
            project["artist"] = str(artist)
        if status:
            project["status"] = str(status)
        
        project["updated_at"] = __import__("time").time()
        return project

    @router.delete("/projects/{project_id}", tags=["Projects"], response_model=dict)
    def archive_project(project_id: str, reason: Optional[str] = None):
        """Archivar un proyecto (no borrar, mantener histórico)."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        
        project["status"] = "archived"
        project["archived_at"] = __import__("time").time()
        if reason:
            project["archive_reason"] = str(reason)
        return project

    # ─────────────────────────────────────────────────────────────────
    # Versiones: CRUD
    # ─────────────────────────────────────────────────────────────────

    @router.get("/projects/{project_id}/versions/{version_name}", tags=["Projects"])
    def get_version(project_id: str, version_name: str):
        """Obtener detalles de una versión específica."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        
        for version in project.get("versions", []):
            if version.get("version_name") == version_name:
                return version
        
        raise HTTPException(404, f"Versión {version_name} no encontrada en {project_id}")

    @router.post("/projects/{project_id}/versions", tags=["Projects"])
    def create_version(
        project_id: str,
        version_name: str,
        job_id: Optional[str] = None,
        preset_snapshot: Optional[dict] = None,
        description: Optional[str] = None,
    ):
        """Crear una versión nueva asociada con un job (resultado de mastering)."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        
        payload = {
            "version_name": str(version_name),
            "job_id": str(job_id) if job_id else None,
            "preset_snapshot": dict(preset_snapshot or {}),
            "description": str(description) if description else None,
        }
        
        jobs.add_version(project_id, version_name, **payload)
        return jobs.get_project(project_id)

    # ─────────────────────────────────────────────────────────────────
    # Exportes: registro y descarga
    # ─────────────────────────────────────────────────────────────────

    @router.post("/projects/{project_id}/versions/{version_name}/exports", tags=["Projects"])
    def register_export(
        project_id: str,
        version_name: str,
        export_id: str,
        export_path: str,
        format: Optional[str] = None,
        bit_depth: Optional[int] = None,
        bitrate: Optional[str] = None,
        platform_target: Optional[str] = None,
    ):
        """Registrar un archivo de exportación en una versión."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        
        if not os.path.exists(export_path):
            raise HTTPException(410, f"Archivo {export_path} no existe")
        
        payload = {
            "format": str(format) if format else None,
            "bit_depth": int(bit_depth) if bit_depth else None,
            "bitrate": str(bitrate) if bitrate else None,
            "platform_target": str(platform_target) if platform_target else None,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        
        jobs.add_export(project_id, version_name, export_id, export_path, **payload)
        return jobs.get_project(project_id)

    @router.get("/projects/{project_id}/versions/{version_name}/download/{export_id}", tags=["Projects"])
    def download_export(
        project_id: str,
        version_name: str,
        export_id: str,
        name: Optional[str] = Query(None, description="Nombre del archivo a descargar"),
    ):
        """Descargar un archivo de exportación específico de una versión."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        
        version = None
        for v in project.get("versions", []):
            if v.get("version_name") == version_name:
                version = v
                break
        
        if not version:
            raise HTTPException(404, f"Versión {version_name} no encontrada")
        
        export = None
        for exp in version.get("exports", []):
            if exp.get("export_id") == export_id:
                export = exp
                break
        
        if not export:
            raise HTTPException(404, f"Exportación {export_id} no encontrada")
        
        export_path = export.get("path")
        if not export_path or not os.path.exists(export_path):
            raise HTTPException(410, "Archivo de exportación expirado o no disponible")
        
        fmt = export.get("format", "wav")
        media_type_map = {
            "mp3": "audio/mpeg",
            "flac": "audio/flac",
            "aiff": "audio/aiff",
            "aac": "audio/aac",
            "wav": "audio/wav",
        }
        media_type = media_type_map.get(fmt, "audio/wav")
        
        # Sanear nombre del proyecto para usarlo en el archivo
        project_name = sanitize_track_name(name or project.get("title", "export"))
        filename = f"{project_name}_{version_name}_{export_id}.{fmt}"
        
        return FileResponse(export_path, media_type=media_type, filename=filename)

    @router.get("/projects/{project_id}/versions/{version_name}/exports", tags=["Projects"])
    def list_exports(project_id: str, version_name: str):
        """Listar todos los exportes de una versión."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        
        for version in project.get("versions", []):
            if version.get("version_name") == version_name:
                return {
                    "version_name": version_name,
                    "exports": version.get("exports", []),
                }
        
        raise HTTPException(404, f"Versión {version_name} no encontrada")

    @router.get("/projects/{project_id}/all-exports", tags=["Projects"])
    def list_all_project_exports(project_id: str):
        """Listar todos los exportes de todas las versiones de un proyecto."""
        try:
            project = jobs.get_project(project_id)
        except KeyError:
            raise HTTPException(404, f"Proyecto {project_id} no encontrado")
        
        all_exports = []
        for version in project.get("versions", []):
            for export in version.get("exports", []):
                export_copy = dict(export)
                export_copy["version_name"] = version.get("version_name")
                all_exports.append(export_copy)
        
        return {"project_id": project_id, "project_title": project.get("title"), "exports": all_exports}

    return router
