import { useEffect, useMemo, useRef, useState } from 'react'

import {
  getCaseReview,
  getCase,
  getDocumentFile,
  updateReviewField,
  uploadCase,
} from '../api/client'
import { DocumentViewer } from '../components/DocumentViewer'
import { FieldList } from '../components/FieldList'
import type {
  CaseReview,
  CaseStatus,
  DocumentFile,
  ReviewField,
  ReviewSource,
} from '../types/api'
import { getReviewSelection } from './reviewSelection'
import './ReviewPage.css'

type ReviewPageProps = {
  caseId: string
}

type LoadState = 'loading' | 'loaded' | 'error'
type ReviewLoadState = 'loading' | 'waiting' | 'loaded' | 'failed' | 'error'
type UploadState = 'idle' | 'uploading' | 'error'

const CASE_POLL_INTERVAL_MS = 2_000

type DocumentLoad = {
  documentId: string
  state: LoadState
  file: DocumentFile | null
  error: string | null
}

function getErrorText(error: unknown): string {
  return error instanceof Error
    ? error.message
    : 'Đã xảy ra lỗi không xác định.'
}

function shortDocumentId(documentId: string): string {
  return documentId.length > 12 ? `${documentId.slice(0, 8)}…` : documentId
}

function sourceLabel(source: ReviewSource, index: number): string {
  return `Nguồn ${index + 1} · Trang ${source.page_number} · ${shortDocumentId(source.document_id)}`
}

export function ReviewPage({ caseId }: ReviewPageProps) {
  const [review, setReview] = useState<CaseReview | null>(null)
  const [reviewState, setReviewState] =
    useState<ReviewLoadState>('loading')
  const [waitingStatus, setWaitingStatus] =
    useState<CaseStatus>('PROCESSING')
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [selectedFieldId, setSelectedFieldId] = useState<string | null>(null)
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null)
  const [documentLoad, setDocumentLoad] = useState<DocumentLoad | null>(null)
  const [pendingFieldIds, setPendingFieldIds] = useState<ReadonlySet<string>>(
    new Set(),
  )
  const [fieldSaveErrors, setFieldSaveErrors] = useState<ReadonlySet<string>>(
    new Set(),
  )
  const [uploadState, setUploadState] = useState<UploadState>('idle')
  const [uploadError, setUploadError] = useState<string | null>(null)
  const documentCache = useRef(new Map<string, DocumentFile>())
  const pendingSaves = useRef(new Set<string>())

  useEffect(() => {
    let isActive = true
    let pollTimer: number | undefined

    async function loadReviewWhenReady() {
      try {
        const currentCase = await getCase(caseId)
        if (!isActive) {
          return
        }
        if (
          currentCase.status === 'UPLOADING' ||
          currentCase.status === 'PROCESSING'
        ) {
          setWaitingStatus(currentCase.status)
          setReviewState('waiting')
          setReviewError(null)
          pollTimer = window.setTimeout(
            () => void loadReviewWhenReady(),
            CASE_POLL_INTERVAL_MS,
          )
          return
        }
        if (currentCase.status === 'FAILED') {
          setWaitingStatus(currentCase.status)
          setReviewState('failed')
          setReviewError(null)
          return
        }

        const loadedReview = await getCaseReview(caseId)
        if (!isActive) {
          return
        }

        const initialField = loadedReview.fields[0] ?? null
        setReview(loadedReview)
        setSelectedFieldId(initialField?.id ?? null)
        setActiveSourceId(initialField?.sources[0]?.ocr_block_id ?? null)
        setReviewState('loaded')
      } catch (error: unknown) {
        if (isActive) {
          setReviewState('error')
          setReviewError(getErrorText(error))
        }
      }
    }

    void loadReviewWhenReady()
    return () => {
      isActive = false
      if (pollTimer !== undefined) {
        window.clearTimeout(pollTimer)
      }
    }
  }, [caseId])

  const selectedField = useMemo(
    () =>
      review?.fields.find((field) => field.id === selectedFieldId) ?? null,
    [review, selectedFieldId],
  )
  const selection = useMemo(
    () => getReviewSelection(selectedField, activeSourceId),
    [activeSourceId, selectedField],
  )
  const selectedDocumentId = selection?.documentId ?? null

  useEffect(() => {
    if (selectedDocumentId === null) {
      return
    }

    const documentId = selectedDocumentId
    let isActive = true

    async function loadDocument() {
      await Promise.resolve()
      if (!isActive) {
        return
      }

      setDocumentLoad({
        documentId,
        state: 'loading',
        file: null,
        error: null,
      })

      try {
        const cachedFile = documentCache.current.get(documentId)
        const loadedFile =
          cachedFile ?? (await getDocumentFile(documentId))
        if (!isActive) {
          return
        }

        documentCache.current.set(documentId, loadedFile)
        setDocumentLoad({
          documentId,
          state: 'loaded',
          file: loadedFile,
          error: null,
        })
      } catch (error: unknown) {
        if (isActive) {
          setDocumentLoad({
            documentId,
            state: 'error',
            file: null,
            error: getErrorText(error),
          })
        }
      }
    }

    void loadDocument()
    return () => {
      isActive = false
    }
  }, [selectedDocumentId])

  function handleSelectField(field: ReviewField) {
    setSelectedFieldId(field.id)
    setActiveSourceId(field.sources[0]?.ocr_block_id ?? null)
  }

  async function handleSaveField(
    field: ReviewField,
    currentValue: string | null,
  ) {
    pendingSaves.current.add(field.id)
    setPendingFieldIds(new Set(pendingSaves.current))
    setFieldSaveErrors((currentErrors) => {
      const nextErrors = new Set(currentErrors)
      nextErrors.delete(field.id)
      return nextErrors
    })

    try {
      const updatedField = await updateReviewField(
        field.case_id,
        field.id,
        currentValue,
      )
      setReview((currentReview) =>
        currentReview === null
          ? null
          : {
              ...currentReview,
              fields: currentReview.fields.map((currentField) =>
                currentField.id === updatedField.id
                  ? { ...currentField, ...updatedField }
                  : currentField,
              ),
            },
      )
    } catch (error: unknown) {
      setFieldSaveErrors((currentErrors) =>
        new Set(currentErrors).add(field.id),
      )
      throw error
    } finally {
      pendingSaves.current.delete(field.id)
      setPendingFieldIds(new Set(pendingSaves.current))
    }
  }

  async function handleUploadCase() {
    if (
      review === null ||
      review.status === 'COMPLETED' ||
      pendingSaves.current.size > 0 ||
      fieldSaveErrors.size > 0
    ) {
      return
    }

    setUploadState('uploading')
    setUploadError(null)
    try {
      const completedCase = await uploadCase(review.case_id)
      setReview((currentReview) =>
        currentReview === null
          ? null
          : { ...currentReview, status: completedCase.status },
      )
      setUploadState('idle')
    } catch (error: unknown) {
      setUploadState('error')
      setUploadError(getErrorText(error))
    }
  }

  const activeDocumentLoad =
    selection !== null && documentLoad?.documentId === selection.documentId
      ? documentLoad
      : null

  if (reviewState === 'loading') {
    return (
      <main className="review-page review-page--message">
        <p role="status">Đang tải dữ liệu hồ sơ...</p>
      </main>
    )
  }

  if (reviewState === 'waiting') {
    return (
      <main className="review-page review-page--message">
        <section className="review-page__waiting" role="status">
          <p className="eyebrow">Smart Sotek IDP · Processing</p>
          <h1>Hồ sơ đang được xử lý</h1>
          <p>
            {waitingStatus === 'UPLOADING'
              ? 'Hồ sơ chưa nhận đủ bốn giấy tờ bắt buộc.'
              : 'OCR và Gemini đang trích xuất thông tin. Trang sẽ tự cập nhật khi hoàn tất.'}
          </p>
        </section>
      </main>
    )
  }

  if (reviewState === 'failed') {
    return (
      <main className="review-page review-page--message">
        <section className="review-page__error" role="alert">
          <h1>Xử lý hồ sơ không thành công</h1>
          <p>
            Pipeline OCR hoặc Gemini đã gặp lỗi. Hồ sơ được đánh dấu FAILED
            thay vì tiếp tục chờ vô hạn.
          </p>
          <a href="/">Quay lại trang tạo hồ sơ</a>
        </section>
      </main>
    )
  }

  if (reviewState === 'error' || review === null) {
    return (
      <main className="review-page review-page--message">
        <section className="review-page__error" role="alert">
          <h1>Không thể mở hồ sơ review</h1>
          <p>{reviewError ?? 'Không nhận được dữ liệu hồ sơ.'}</p>
        </section>
      </main>
    )
  }

  return (
    <main className="review-page">
      <header className="review-page__header">
        <div>
          <p className="eyebrow">Smart Sotek IDP · Review</p>
          <h1>Kiểm tra thông tin hồ sơ</h1>
          <p className="review-page__case-id">Mã hồ sơ: {review.case_id}</p>
        </div>
        <div className="review-page__actions">
          <span className="status-badge">{review.status}</span>
          <button
            type="button"
            onClick={() => void handleUploadCase()}
            disabled={
              review.status === 'COMPLETED' ||
              uploadState === 'uploading' ||
              pendingFieldIds.size > 0 ||
              fieldSaveErrors.size > 0
            }
          >
            {review.status === 'COMPLETED'
              ? 'Đã Upload'
              : uploadState === 'uploading'
                ? 'Đang Upload...'
                : 'Upload hồ sơ'}
          </button>
          {pendingFieldIds.size > 0 ? (
            <span className="review-page__action-status" role="status">
              Đang lưu {pendingFieldIds.size} thay đổi...
            </span>
          ) : fieldSaveErrors.size > 0 ? (
            <span className="review-page__action-error" role="alert">
              Còn thay đổi lưu lỗi. Hãy sửa hoặc thử lưu lại trước khi Upload.
            </span>
          ) : uploadError !== null ? (
            <span className="review-page__action-error" role="alert">
              {uploadError}
            </span>
          ) : null}
        </div>
      </header>

      <div className="review-workspace">
        <FieldList
          fields={review.fields}
          selectedFieldId={selectedFieldId}
          isEditable={review.status === 'READY_FOR_REVIEW'}
          onSelectField={handleSelectField}
          onSaveField={handleSaveField}
        />

        <section className="review-evidence" aria-labelledby="evidence-title">
          <header className="review-evidence__header">
            <div>
              <p className="eyebrow">Đối chiếu tài liệu</p>
              <h2 id="evidence-title">
                {selectedField === null
                  ? 'Chọn một trường'
                  : `Bằng chứng cho ${selectedField.field_code}`}
              </h2>
            </div>
            {selection !== null ? (
              <span>Trang {selection.pageNumber}</span>
            ) : null}
          </header>

          {selectedField !== null && selectedField.sources.length > 1 ? (
            <nav className="source-selector" aria-label="Chọn nguồn bằng chứng">
              {selectedField.sources.map((source, index) => (
                <button
                  type="button"
                  className={
                    source.ocr_block_id === selection?.activeSource.ocr_block_id
                      ? 'source-selector__button source-selector__button--active'
                      : 'source-selector__button'
                  }
                  onClick={() => setActiveSourceId(source.ocr_block_id)}
                  key={source.ocr_block_id}
                >
                  {sourceLabel(source, index)}
                </button>
              ))}
            </nav>
          ) : null}

          <div className="review-evidence__viewer">
            {selection === null ? (
              <p className="review-evidence__empty">
                Trường này chưa có vùng bằng chứng. Chuyên viên có thể bổ sung
                thủ công ở bước chỉnh sửa tiếp theo.
              </p>
            ) : activeDocumentLoad === null ||
              activeDocumentLoad.state === 'loading' ? (
              <p className="review-evidence__empty" role="status">
                Đang tải tài liệu nguồn...
              </p>
            ) : activeDocumentLoad.state === 'error' ||
              activeDocumentLoad.file === null ? (
              <p className="review-evidence__error" role="alert">
                {activeDocumentLoad.error ?? 'Không thể tải tài liệu nguồn.'}
              </p>
            ) : activeDocumentLoad.file.documentType === 'pdf' ? (
              <DocumentViewer
                documentType="pdf"
                source={activeDocumentLoad.file.blob}
                pageNumber={selection.pageNumber}
                highlights={selection.highlights}
                label="Tài liệu nguồn của trường đã chọn"
              />
            ) : (
              <DocumentViewer
                documentType="image"
                source={activeDocumentLoad.file.blob}
                highlights={selection.highlights}
                alt="Tài liệu nguồn của trường đã chọn"
              />
            )}
          </div>
        </section>
      </div>
    </main>
  )
}
