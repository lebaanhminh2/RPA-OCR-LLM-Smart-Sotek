import { useState, type ChangeEvent } from 'react'

import { createCase, getCase, uploadDocument } from '../api/client'
import type { Case, Document, DocumentType } from '../types/api'

const DOCUMENT_ROWS: ReadonlyArray<{
  label: string
  type: DocumentType
}> = [
  { label: 'CCCD mặt trước', type: 'CCCD_FRONT' },
  { label: 'CCCD mặt sau', type: 'CCCD_BACK' },
  { label: 'Giấy đề nghị vay vốn', type: 'LOAN_APPLICATION' },
  { label: 'Hợp đồng lao động', type: 'LABOR_CONTRACT' },
]

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

export function CaseUploadPage() {
  const [currentCase, setCurrentCase] = useState<Case | null>(null)
  const [isCreatingCase, setIsCreatingCase] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [uploadStates, setUploadStates] = useState<UploadStates>(
    createInitialUploadStates,
  )

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
              <p className="processing-message">
                Hồ sơ đã đủ giấy tờ và đang chờ xử lý.
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
