import type {
  Case,
  CaseReview,
  CompletedCase,
  Document,
  DocumentFile,
  DocumentType,
  UpdatedReviewField,
} from '../types/api'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'
export const DEMO_CASE_ID = 'demo-latest'
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, '')

type DemoPayload = {
  case: Case
  review: CaseReview
  documents: Record<string, string>
}

let demoPayload: DemoPayload | null = null

export function isDemoCaseId(caseId: string): boolean {
  return caseId === DEMO_CASE_ID
}

async function getDemoPayload(): Promise<DemoPayload> {
  if (demoPayload !== null) {
    return demoPayload
  }

  const response = await fetch('/demo-data.json')
  if (!response.ok) {
    throw new Error('Không thể tải dữ liệu demo.')
  }
  demoPayload = (await response.json()) as DemoPayload
  return demoPayload
}

type ApiError = {
  detail: string | { message?: string }
}

function isApiError(value: unknown): value is ApiError {
  return (
    typeof value === 'object' &&
    value !== null &&
    'detail' in value &&
    (typeof value.detail === 'string' ||
      (typeof value.detail === 'object' && value.detail !== null))
  )
}

async function getErrorMessage(response: Response): Promise<string> {
  const fallbackMessage = `Yêu cầu thất bại (HTTP ${response.status}).`

  try {
    const body: unknown = await response.json()
    if (!isApiError(body)) {
      return fallbackMessage
    }
    if (typeof body.detail === 'string') {
      return body.detail
    }
    return typeof body.detail.message === 'string'
      ? body.detail.message
      : fallbackMessage
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
  if (isDemoCaseId(caseId)) {
    return { ...(await getDemoPayload()).case }
  }
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

export async function getCaseReview(caseId: string): Promise<CaseReview> {
  if (isDemoCaseId(caseId)) {
    return structuredClone((await getDemoPayload()).review)
  }
  const response = await fetch(
    `${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/review`,
  )
  return parseResponse<CaseReview>(response)
}

export async function updateReviewField(
  caseId: string,
  fieldId: string,
  currentValue: string | null,
): Promise<UpdatedReviewField> {
  if (isDemoCaseId(caseId)) {
    const payload = await getDemoPayload()
    const field = payload.review.fields.find(
      (candidate) => candidate.id === fieldId,
    )
    if (field === undefined) {
      throw new Error('Không tìm thấy trường dữ liệu demo.')
    }
    field.current_value = currentValue
    return {
      id: field.id,
      case_id: field.case_id,
      field_code: field.field_code,
      original_value: field.original_value,
      current_value: field.current_value,
    }
  }
  const response = await fetch(
    `${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/fields/${encodeURIComponent(fieldId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_value: currentValue }),
    },
  )
  return parseResponse<UpdatedReviewField>(response)
}

export async function uploadCase(caseId: string): Promise<CompletedCase> {
  const response = await fetch(
    `${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/upload`,
    { method: 'POST' },
  )
  return parseResponse<CompletedCase>(response)
}

export async function getDocumentFile(
  documentId: string,
): Promise<DocumentFile> {
  const demoDocumentPath = demoPayload?.documents[documentId]
  if (demoDocumentPath !== undefined) {
    const response = await fetch(demoDocumentPath)
    if (!response.ok) {
      throw new Error('Không thể tải tài liệu demo.')
    }
    return { blob: await response.blob(), documentType: 'pdf' }
  }

  const response = await fetch(
    `${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/file`,
  )
  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  const blob = await response.blob()
  const mediaType = (response.headers.get('content-type') || blob.type)
    .split(';', 1)[0]
    .trim()
    .toLowerCase()
  if (mediaType === 'application/pdf') {
    return { blob, documentType: 'pdf' }
  }
  if (mediaType.startsWith('image/')) {
    return { blob, documentType: 'image' }
  }
  throw new Error(
    `Định dạng tài liệu không được hỗ trợ: ${mediaType || 'không xác định'}.`,
  )
}
