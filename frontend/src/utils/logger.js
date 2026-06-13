/**
 * 前端运行时调试日志工具
 *
 * 提供带时间戳和级别的控制台日志，方便调试 API 调用、状态变化等。
 * 浏览器环境无法直接写文件，日志输出到 DevTools Console。
 *
 * 用法:
 *   import { logger } from '@/utils/logger'
 *   logger.info('loadHistory', 'Fetching history...', { page: 1 })
 *   logger.error('saveHistory', 'Failed to save', err)
 *
 * 日志格式:
 *   [2024-01-15T10:30:00.000Z] INFO  [loadHistory] Fetching history... { page: 1 }
 */

const LEVELS = ['DEBUG', 'INFO', 'WARN', 'ERROR']

const LOG_LEVEL = import.meta.env.DEV ? 'DEBUG' : 'INFO'

const LEVEL_PRIORITY = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 }

function shouldLog(level) {
  return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[LOG_LEVEL]
}

function timestamp() {
  return new Date().toISOString()
}

function formatMessage(level, tag, message, data) {
  let line = `[${timestamp()}] ${level.padEnd(5)} [${tag}] ${message}`
  if (data !== undefined) {
    try {
      line += ' ' + JSON.stringify(data)
    } catch {
      line += ' ' + String(data)
    }
  }
  return line
}

function createLogger(defaultTag = 'app') {
  return {
    debug(tag, message, data) {
      if (shouldLog('DEBUG')) console.debug(formatMessage('DEBUG', tag, message, data))
    },
    info(tag, message, data) {
      if (shouldLog('INFO')) console.info(formatMessage('INFO', tag, message, data))
    },
    warn(tag, message, data) {
      if (shouldLog('WARN')) console.warn(formatMessage('WARN', tag, message, data))
    },
    error(tag, message, data) {
      if (shouldLog('ERROR')) console.error(formatMessage('ERROR', tag, message, data))
    },
  }
}

export const logger = createLogger('app')

/**
 * 为 axios 请求/响应创建日志中间件
 * 用法:
 *   api.interceptors.request.use(logRequest)
 *   api.interceptors.response.use(logResponse, logError)
 */
export function logRequest(config) {
  if (shouldLog('DEBUG')) {
    console.debug(
      formatMessage('DEBUG', 'api', `→ ${config.method?.toUpperCase()} ${config.url}`, {
        params: config.params,
        data: config.data,
      }),
    )
  }
  return config
}

export function logResponse(response) {
  if (shouldLog('DEBUG')) {
    const { status, config } = response
    console.debug(
      formatMessage('DEBUG', 'api', `← ${status} ${config.method?.toUpperCase()} ${config.url}`),
    )
  }
  return response
}

export function logError(error) {
  const { response, config, message } = error
  const status = response?.status || 'N/A'
  const url = config?.url || 'unknown'
  const detail = response?.data?.detail || message

  console.error(
    formatMessage('ERROR', 'api', `✗ ${status} ${config?.method?.toUpperCase() || '?'} ${url}`, {
      detail,
      requestBody: config?.data,
      responseBody: response?.data,
    }),
  )
  return Promise.reject(error)
}

export default { logger, logRequest, logResponse, logError }
