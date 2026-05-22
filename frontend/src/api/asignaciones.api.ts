import { api, postForm } from './client'

/**
 *   GET   /asignaciones/crear/   → formulario
 *   POST  /asignaciones/crear/   → crea asignación
 *   (las rutas /asignaciones/ y /asignaciones/<id>/ no parecen exponerse desde fuera de sesión;
 *    se asumen accesibles tras login)
 */
export const asignacionesApi = {
  list:   () => api.get<string>('/asignaciones/'),
  create: (data: Record<string, string | number | boolean>) =>
    postForm('/asignaciones/crear/', data),
}
