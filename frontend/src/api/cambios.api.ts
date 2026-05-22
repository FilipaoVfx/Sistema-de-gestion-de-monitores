/**
 * El backend desplegado NO expone /solicitudes/ ni /cambios/ (ambos retornan 404).
 * Esta capa queda como placeholder hasta que el backend agregue dichas rutas.
 */
import { postForm, api } from './client'

export const cambiosApi = {
  list:    () => api.get<string>('/cambios/'),
  create:  (data: Record<string, string | number | boolean>) =>
    postForm('/cambios/crear/', data),
  aprobar: (id: number) => postForm(`/cambios/${id}/aprobar/`, {}),
  rechazar:(id: number) => postForm(`/cambios/${id}/rechazar/`, {}),
}
