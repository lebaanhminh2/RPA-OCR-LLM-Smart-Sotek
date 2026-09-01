export type CaseStatus =
  | 'UPLOADING'
  | 'PROCESSING'
  | 'READY_FOR_REVIEW'
  | 'COMPLETED'
  | 'FAILED'

export type Case = {
  id: string
  status: CaseStatus
  created_at: string
  updated_at: string
}

export type DocumentType =
  | 'CCCD_FRONT'
  | 'CCCD_BACK'
  | 'LOAN_APPLICATION'
  | 'LABOR_CONTRACT'

export type DocumentOcrStatus = 'PENDING' | 'DONE' | 'FAILED'

export type Document = {
  id: string
  case_id: string
  document_type: DocumentType
  file_path: string
  page_count: number
  ocr_status: DocumentOcrStatus
  uploaded_at: string
}
