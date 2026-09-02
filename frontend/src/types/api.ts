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

export type ReviewSource = {
  ocr_block_id: string
  document_id: string
  page_number: number
  bbox_x: number
  bbox_y: number
  bbox_width: number
  bbox_height: number
}

export type ReviewField = {
  id: string
  case_id: string
  field_code: string
  original_value: string | null
  current_value: string | null
  sources: ReviewSource[]
}

export type CaseReview = {
  case_id: string
  status: Extract<CaseStatus, 'READY_FOR_REVIEW' | 'COMPLETED'>
  fields: ReviewField[]
}

export type DocumentFile = {
  blob: Blob
  documentType: 'pdf' | 'image'
}
