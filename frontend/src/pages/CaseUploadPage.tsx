import { useEffect, useState, type ChangeEvent } from 'react'

import { createCase, getCase, uploadDocument } from '../api/client'
import type { Case, Document, DocumentType } from '../types/api'
import {
  DEMO_DOCUMENTS,
  DEMO_PROCESSING_DELAY_MS,
  getDemoReviewUrl,
  getNextDemoStage,
  type DemoStage,
} from './demoWorkflow'

const DOCUMENT_ROWS: ReadonlyArray<{
  label: string
  type: DocumentType
}> = [
  { label: 'CCCD mặt trước', type: 'CCCD_FRONT' },
  { label: 'CCCD mặt sau', type: 'CCCD_BACK' },
  { label: 'Giấy đề nghị vay vốn', type: 'LOAN_APPLICATION' },
  { label: 'Hợp đồng lao động', type: 'LABOR_CONTRACT' },
]

const CASE_POLL_INTERVAL_MS = 2_000

type UploadPhase = 'idle' | 'uploading' | 'success' | 'error'

type UploadState = {
  file: File | null
  phase: UploadPhase
  message: string | null
  document: Document | null
}

type UploadStates = Record<DocumentType, UploadState>

function createInitialUploadStates(): UploadStates {
  return {
    CCCD_FRONT: { file: null, phase: 'idle', message: null, document: null },
    CCCD_BACK: { file: null, phase: 'idle', message: null, document: null },
    LOAN_APPLICATION: {
      file: null,
      phase: 'idle',
      message: null,
      document: null,
    },
    LABOR_CONTRACT: {
      file: null,
      phase: 'idle',
      message: null,
      document: null,
    },
  }
}

function getErrorText(error: unknown): string {
  return error instanceof Error ? error.message : 'Đã xảy ra lỗi không xác định.'
}

type CaseUploadPageProps = {
  isDemoMode?: boolean
}

function DemoUploadPage() {
  const [stage, setStage] = useState<DemoStage>('empty')

  function handlePrimaryAction() {
    const nextStage = getNextDemoStage(stage)
    setStage(nextStage)
    if (nextStage === 'processing') {
      window.setTimeout(() => {
        window.location.assign(getDemoReviewUrl())
      }, DEMO_PROCESSING_DELAY_MS)
    }
  }

  return (
    <main className="page-shell">
      <section className="upload-card" aria-labelledby="demo-title">
        <header className="page-header">
          <div>
            <p className="eyebrow">Smart Sotek IDP · Portfolio demo</p>
            <h1 id="demo-title">Xử lý hồ sơ vay từ lương</h1>
          </div>
          <span className="demo-mode-badge">Không cần backend</span>
        </header>

        <p className="demo-introduction">
          Trải nghiệm luồng Upload → OCR/LLM → Review bằng bộ hồ sơ mẫu đã xử
          lý. Demo không gửi và không lưu dữ liệu; mọi chỉnh sửa được đặt lại
          khi tải lại trang.
        </p>

        <section className="case-summary" aria-label="Hồ sơ demo">
          <div>
            <span>Mã hồ sơ</span>
            <strong>DEMO-SALARY-LOAN-001</strong>
          </div>
          <div>
            <span>Trạng thái</span>
            <strong className="status-badge">
              {stage === 'empty'
                ? 'CHƯA CHỌN HỒ SƠ'
                : stage === 'ready'
                  ? 'SẴN SÀNG XỬ LÝ'
                  : 'PROCESSING'}
            </strong>
          </div>
          {stage === 'processing' ? (
            <div className="processing-message" role="status">
              <span className="processing-spinner" aria-hidden="true" />
              <div>
                <strong>Đang mô phỏng pipeline OCR và Gemini</strong>
                <span>
                  Phát hiện vùng chữ → nhận dạng tiếng Việt → trích xuất 40
                  trường → map nguồn bằng chứng.
                </span>
              </div>
            </div>
          ) : null}
        </section>

        <section className="document-list" aria-labelledby="demo-documents">
          <h2 id="demo-documents">Bốn giấy tờ bắt buộc</h2>
          {DEMO_DOCUMENTS.map((document) => (
            <article
              className="document-row demo-document-row"
              key={document.type}
            >
              <div className="document-info">
                <h3>{document.label}</h3>
                <span>{document.type}</span>
              </div>
              <p className="demo-document-detail">
                {document.pages} trang · PDF mẫu
              </p>
              <span
                className={
                  stage === 'empty'
                    ? 'demo-document-status'
                    : 'demo-document-status demo-document-status--ready'
                }
              >
                {stage === 'empty' ? 'Chờ chọn' : 'Đã tải lên'}
              </span>
            </article>
          ))}
        </section>

        <footer className="demo-actions">
          <p>
            {stage === 'empty'
              ? 'Bắt đầu bằng bộ tài liệu synthetic đã chuẩn bị sẵn.'
              : stage === 'ready'
                ? 'Hồ sơ đã đủ giấy tờ và sẵn sàng chạy pipeline demo.'
                : 'Sau khi xử lý, trang Review sẽ tự động mở.'}
          </p>
          <button
            type="button"
            onClick={handlePrimaryAction}
            disabled={stage === 'processing'}
          >
            {stage === 'empty'
              ? 'Sử dụng bộ hồ sơ mẫu'
              : stage === 'ready'
                ? 'Chạy xử lý demo'
                : 'Đang xử lý...'}
          </button>
        </footer>
      </section>
    </main>
  )
}

function LiveCaseUploadPage() {
  const [currentCase, setCurrentCase] = useState<Case | null>(null)
  const [isCreatingCase, setIsCreatingCase] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [uploadStates, setUploadStates] = useState<UploadStates>(
    createInitialUploadStates,
  )

  const currentCaseId = currentCase?.id ?? null
  const currentCaseStatus = currentCase?.status ?? null

  useEffect(() => {
    if (currentCaseId === null || currentCaseStatus !== 'PROCESSING') {
      return
    }

    const caseId = currentCaseId
    let isActive = true
    let pollTimer: number | undefined

    async function pollCaseStatus() {
      try {
        const refreshedCase = await getCase(caseId)
        if (!isActive) {
          return
        }
        setCurrentCase(refreshedCase)
        setPageError(null)
        if (refreshedCase.status === 'PROCESSING') {
          pollTimer = window.setTimeout(
            () => void pollCaseStatus(),
            CASE_POLL_INTERVAL_MS,
          )
        }
      } catch (error: unknown) {
        if (!isActive) {
          return
        }
        setPageError(
          `Chưa thể cập nhật tiến độ xử lý: ${getErrorText(error)}. Hệ thống sẽ thử lại.`,
        )
        pollTimer = window.setTimeout(
          () => void pollCaseStatus(),
          CASE_POLL_INTERVAL_MS,
        )
      }
    }

    void pollCaseStatus()
    return () => {
      isActive = false
      if (pollTimer !== undefined) {
        window.clearTimeout(pollTimer)
      }
    }
  }, [currentCaseId, currentCaseStatus])

  async function handleCreateCase() {
    setIsCreatingCase(true)
    setPageError(null)

    try {
      const createdCase = await createCase()
      setCurrentCase(createdCase)
      setUploadStates(createInitialUploadStates())
    } catch (error: unknown) {
      setPageError(getErrorText(error))
    } finally {
      setIsCreatingCase(false)
    }
  }

  function handleFileChange(
    documentType: DocumentType,
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0] ?? null
    setUploadStates((states) => ({
      ...states,
      [documentType]: {
        file,
        phase: 'idle',
        message: null,
        document: null,
      },
    }))
  }

  async function handleUpload(documentType: DocumentType) {
    if (currentCase === null) {
      setPageError('Vui lòng tạo hồ sơ trước khi tải tài liệu.')
      return
    }

    const uploadState = uploadStates[documentType]
    if (uploadState.file === null) {
      setUploadStates((states) => ({
        ...states,
        [documentType]: {
          ...states[documentType],
          phase: 'error',
          message: 'Vui lòng chọn một tệp.',
        },
      }))
      return
    }

    const caseId = currentCase.id
    const file = uploadState.file
    setPageError(null)
    setUploadStates((states) => ({
      ...states,
      [documentType]: {
        ...states[documentType],
        phase: 'uploading',
        message: null,
      },
    }))

    try {
      const document = await uploadDocument(caseId, documentType, file)
      setUploadStates((states) => ({
        ...states,
        [documentType]: {
          ...states[documentType],
          phase: 'success',
          message: 'Tải lên thành công.',
          document,
        },
      }))

      try {
        const refreshedCase = await getCase(caseId)
        setCurrentCase(refreshedCase)
      } catch (error: unknown) {
        setPageError(
          `Tài liệu đã tải lên nhưng không thể cập nhật trạng thái hồ sơ: ${getErrorText(error)}`,
        )
      }
    } catch (error: unknown) {
      setUploadStates((states) => ({
        ...states,
        [documentType]: {
          ...states[documentType],
          phase: 'error',
          message: getErrorText(error),
        },
      }))
    }
  }

  return (
    <main className="page-shell">
      <section className="upload-card" aria-labelledby="page-title">
        <header className="page-header">
          <div>
            <p className="eyebrow">Smart Sotek IDP</p>
            <h1 id="page-title">Tạo và tải hồ sơ vay</h1>
          </div>
          <button
            type="button"
            onClick={handleCreateCase}
            disabled={isCreatingCase}
          >
            {isCreatingCase ? 'Đang tạo...' : 'Tạo hồ sơ mới'}
          </button>
        </header>

        {pageError !== null ? (
          <p className="message message-error" role="alert">
            {pageError}
          </p>
        ) : null}

        {currentCase !== null ? (
          <section className="case-summary" aria-label="Thông tin hồ sơ">
            <div>
              <span>Mã hồ sơ</span>
              <strong>{currentCase.id}</strong>
            </div>
            <div>
              <span>Trạng thái</span>
              <strong className="status-badge">{currentCase.status}</strong>
            </div>
            {currentCase.status === 'PROCESSING' ? (
              <div
                className="processing-message"
                role="status"
                aria-live="polite"
              >
                <span className="processing-spinner" aria-hidden="true" />
                <div>
                  <strong>Đang OCR và trích xuất thông tin</strong>
                  <span>
                    Thường mất khoảng 2–3 phút trên cấu hình chuẩn. Trang này
                    sẽ tự cập nhật khi hoàn tất.
                  </span>
                </div>
              </div>
            ) : null}
            {currentCase.status === 'READY_FOR_REVIEW' ? (
              <div className="case-ready-message">
                <p>Đã xử lý xong. Hồ sơ sẵn sàng để kiểm tra.</p>
                <a href={`/?case_id=${encodeURIComponent(currentCase.id)}`}>
                  Mở màn hình Review
                </a>
              </div>
            ) : null}
            {currentCase.status === 'FAILED' ? (
              <p className="case-failed-message" role="alert">
                Không thể xử lý hồ sơ. Vui lòng kiểm tra cấu hình OCR/Gemini
                hoặc tạo hồ sơ mới để thử lại.
              </p>
            ) : null}
          </section>
        ) : (
          <p className="empty-state">
            Tạo hồ sơ mới để bắt đầu tải lên bốn giấy tờ bắt buộc.
          </p>
        )}

        <section className="document-list" aria-labelledby="documents-title">
          <h2 id="documents-title">Giấy tờ bắt buộc</h2>
          {DOCUMENT_ROWS.map((row) => {
            const state = uploadStates[row.type]
            const isUploading = state.phase === 'uploading'
            const isUploaded = state.phase === 'success'

            return (
              <article className="document-row" key={row.type}>
                <div className="document-info">
                  <h3>{row.label}</h3>
                  <span>{row.type}</span>
                </div>
                <label className="file-picker">
                  <span className="sr-only">Chọn tệp {row.label}</span>
                  <input
                    type="file"
                    accept="application/pdf,image/*"
                    onChange={(event) => handleFileChange(row.type, event)}
                    disabled={currentCase === null || isUploading || isUploaded}
                  />
                </label>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => handleUpload(row.type)}
                  disabled={
                    currentCase === null ||
                    state.file === null ||
                    isUploading ||
                    isUploaded
                  }
                >
                  {isUploading
                    ? 'Đang tải...'
                    : isUploaded
                      ? 'Đã tải lên'
                      : 'Tải lên'}
                </button>
                <p
                  className={`upload-result upload-${state.phase}`}
                  aria-live="polite"
                >
                  {state.message ??
                    (state.file !== null ? state.file.name : 'Chưa chọn tệp')}
                </p>
              </article>
            )
          })}
        </section>
      </section>
    </main>
  )
}

export function CaseUploadPage({ isDemoMode = false }: CaseUploadPageProps) {
  return isDemoMode ? <DemoUploadPage /> : <LiveCaseUploadPage />
}
