import api from './index'

export function getEnvConfig() {
  return api.get('/system/admin/env')
}

export function updateEnvConfig(settings) {
  return api.put('/system/admin/env', { settings })
}
