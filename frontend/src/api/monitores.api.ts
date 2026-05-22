import { api, postForm } from './client'

/**
 *   GET    /monitores/         → listado
 *   GET    /monitores/crear/   → form
 *   POST   /monitores/crear/   → crear
 */
export const monitoresApi = {
  list:   () => api.get<string>('/monitores/'),
  create: (data: Record<string, string | number | boolean>) => postForm('/monitores/crear/', data),
}

export const usuariosApi = {
  list: () => api.get<string>('/usuarios/'),
}
