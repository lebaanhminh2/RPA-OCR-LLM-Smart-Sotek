import { useEffect, useMemo, useRef, useState } from 'react'

import { getCaseReview, getDocumentFile } from '../api/client'
import { DocumentViewer } from '../components/DocumentViewer'
import { FieldList } from '../components/FieldList'
import type {
  CaseReview,
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
  const [reviewState, setReviewState] = useState<LoadState>('loading')
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [selectedFieldId, setSelectedFieldId] = useState<string | null>(null)
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null)
  const [documentLoad, setDocumentLoad] = useState<DocumentLoad | null>(null)
  const documentCache = useRef(new Map<string, DocumentFile>())

  useEffect(() => {
    let isActive = true

    async function loadReview() {
      setReviewState('loading')
      setReviewError(null)

      try {
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

    void loadReview()
    return () => {
      isActive = false
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
        <span className="status-badge">{review.status}</span>
      </header>

      <div className="review-workspace">
        <FieldList
          fields={review.fields}
          selectedFieldId={selectedFieldId}
          onSelectField={handleSelectField}
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
