import { api, postForm } from './client'

/**
 *   GET   /horarios/          → listado (protegido)
 *   GET   /horarios/crear/    → formulario
 *   POST  /horarios/crear/    → crea horario
 */
export const horariosApi = {
  list:   () => api.get<string>('/horarios/'),
  create: (data: Record<string, string | number | boolean>) =>
    postForm('/horarios/crear/', data),
}
