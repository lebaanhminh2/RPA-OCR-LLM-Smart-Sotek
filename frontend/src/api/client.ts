import type { Case, Document, DocumentType } from '../types/api'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, '')

type ApiError = {
  detail: string
}

function isApiError(value: unknown): value is ApiError {
  return (
    typeof value === 'object' &&
    value !== null &&
    'detail' in value &&
    typeof value.detail === 'string'
  )
}

async function getErrorMessage(response: Response): Promise<string> {
  const fallbackMessage = `Yêu cầu thất bại (HTTP ${response.status}).`

  try {
    const body: unknown = await response.json()
    return isApiError(body) ? body.detail : fallbackMessage
  } catch {
    return fallbackMessage
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json() as Promise<T>
}

export async function createCase(): Promise<Case> {
  const response = await fetch(`${API_BASE_URL}/cases`, {
    method: 'POST',
  })
  return parseResponse<Case>(response)
}

export async function getCase(caseId: string): Promise<Case> {
  const response = await fetch(
    `${API_BASE_URL}/cases/${encodeURIComponent(caseId)}`,
  )
  return parseResponse<Case>(response)
}

export async function uploadDocument(
  caseId: string,
  documentType: DocumentType,
  file: File,
): Promise<Document> {
  const body = new FormData()
  body.append('document_type', documentType)
  body.append('file', file)

  const response = await fetch(
    `${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/documents`,
    {
      method: 'POST',
      body,
    },
  )
  return parseResponse<Document>(response)
}
