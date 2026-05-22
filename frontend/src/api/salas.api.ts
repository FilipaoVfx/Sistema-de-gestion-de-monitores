import { api, postForm } from './client'
import type { Sala } from '../types/sala.types'

/**
 * Backend Django+HTMX expone:
 *   GET    /salas/                      → HTML listado (protegido)
 *   GET    /salas/crear/                → HTML formulario
 *   POST   /salas/crear/                → procesa form, redirige
 *   GET    /salas/<id>/editar/          → HTML form de edición
 *   POST   /salas/<id>/editar/          → procesa edición
 *   POST   /salas/<id>/eliminar/        → elimina
 *
 * No hay endpoint JSON. Estas funciones disparan las URLs reales;
 * el parseo de HTML se hace en la capa de página (placeholder).
 */
export const salasApi = {
  list:   () => api.get<string>('/salas/'),
  get:    (id: number)  => api.get<string>(`/salas/${id}/editar/`),
  create: (data: Record<string, string | number | boolean>) => postForm('/salas/crear/', data),
  update: (id: number, data: Record<string, string | number | boolean>) =>
    postForm(`/salas/${id}/editar/`, data),
  remove: (id: number)  => postForm(`/salas/${id}/eliminar/`, {}),
}

// Helper preparado para cuando el backend exponga JSON
export type SalaListItem = Sala
