"""
Módulo de autenticación JWT para Audit Service.
Compatible con el sistema de autenticación de UsersMachPay y AppMachineryPayrollBackend.
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError


# Excepción personalizada para errores de permisos
class PermissionDenied(Exception):
    """Excepción lanzada cuando un usuario no tiene permisos suficientes."""
    def __init__(self, message: str = "No tiene permisos para listar logs del sistema."):
        self.message = message
        super().__init__(self.message)

# Configuración JWT (debe ser la misma SECRET_KEY que UsersMachPay)
SECRET_KEY = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET o SECRET_KEY no está definido en el entorno")

# OAuth2 scheme para extraer el token del header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class AuthService:
    """Servicio de autenticación para validar JWT y permisos."""
    
    @staticmethod
    def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
        """
        Valida el token JWT y retorna el payload del usuario.
        
        Args:
            token: Token JWT extraído del header Authorization: Bearer <token>
            
        Returns:
            dict: Payload completo del JWT con estructura:
                {
                    "id": int,
                    "email": str,
                    "name": str,
                    "rol": [
                        {
                            "id": int,
                            "name": str,
                            "permisos": [{"id": int, "name": str, "description": str}]
                        }
                    ],
                    "status": int,
                    "first_login": bool,
                    "exp": int
                }
                
        Raises:
            HTTPException: Si el token es inválido, expirado o mal formado
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudieron validar las credenciales",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            # Decodificar JWT con la misma clave secreta que UsersMachPay
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Validar que el payload tenga los campos mínimos requeridos
            user_id: Optional[int] = payload.get("id")
            email: Optional[str] = payload.get("email") or payload.get("sub")
            
            if user_id is None or email is None:
                raise credentials_exception
                
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError:
            raise credentials_exception


def check_permission(current_user: dict, required_permission_id: int) -> bool:
    """
    Verifica si el usuario tiene un permiso específico.
    
    Args:
        current_user: Payload del JWT obtenido de AuthService.get_current_user()
        required_permission_id: ID del permiso requerido (ej: 200 para audit.logs.view)
        
    Returns:
        bool: True si el usuario tiene el permiso, False en caso contrario
        
    Ejemplo:
        current_user = {
            "rol": [
                {
                    "id": 1,
                    "name": "Administrador",
                    "permisos": [
                        {"id": 200, "name": "audit.logs.view", "description": "Ver logs de auditoría"},
                        {"id": 201, "name": "audit.logs.export", "description": "Exportar logs"}
                    ]
                }
            ]
        }
        
        check_permission(current_user, 200)  # True
        check_permission(current_user, 999)  # False
    """
    # Obtener roles del payload (soporta "rol" y "roles" por compatibilidad)
    user_roles = current_user.get("rol") or current_user.get("roles") or []
    
    # Extraer todos los IDs de permisos de todos los roles del usuario
    permisos_usuario = []
    for rol in user_roles:
        # Obtener permisos del rol (soporta "permisos" y "permissions")
        perms = rol.get("permisos") or rol.get("permissions") or []
        for perm in perms:
            if isinstance(perm, dict) and "id" in perm:
                permisos_usuario.append(perm.get("id"))
    
    # Verificar si el usuario tiene el permiso requerido
    return required_permission_id in permisos_usuario


def require_permission(required_permission_id: int):
    """
    Dependency para validar que el usuario tenga un permiso específico.
    
    Args:
        required_permission_id: ID del permiso requerido
        
    Returns:
        dict: Payload del usuario si tiene el permiso
        
    Raises:
        PermissionDenied: Si el usuario no tiene el permiso requerido
        
    Uso en endpoints:
        @app.get("/audit-events")
        def list_events(current_user: dict = Depends(require_permission(200))):
            # Solo usuarios con permiso 200 pueden acceder
            ...
    """
    def _check(current_user: dict = Depends(AuthService.get_current_user)) -> dict:
        if not check_permission(current_user, required_permission_id):
            raise PermissionDenied()
        return current_user
    
    return _check
