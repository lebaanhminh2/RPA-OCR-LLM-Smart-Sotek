import {
  GlobalWorkerOptions,
  RenderingCancelledException,
  getDocument,
  type PDFDocumentLoadingTask,
  type PDFDocumentProxy,
  type RenderTask,
} from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { useEffect, useRef, useState, type RefObject } from 'react'

import {
  normalizedBboxToPixelRectangle,
  type DisplayedPageDimensions,
  type NormalizedBbox,
} from './bboxGeometry'
import './DocumentViewer.css'

GlobalWorkerOptions.workerSrc = pdfWorkerUrl

type SharedDocumentViewerProps = {
  source: string | Blob
  highlight?: NormalizedBbox
}

export type DocumentViewerProps =
  | (SharedDocumentViewerProps & {
      documentType: 'pdf'
      label?: string
    })
  | (SharedDocumentViewerProps & {
      documentType: 'image'
      alt: string
    })

type LoadState = 'loading' | 'loaded' | 'error'
type ZoomLevel = 1 | 1.5

const blobSourceIds = new WeakMap<Blob, number>()
let nextBlobSourceId = 1

function getImageSourceKey(source: string | Blob): string {
  if (typeof source === 'string') {
    return source
  }

  const existingId = blobSourceIds.get(source)
  if (existingId !== undefined) {
    return `blob-${existingId}`
  }

  const sourceId = nextBlobSourceId
  nextBlobSourceId += 1
  blobSourceIds.set(source, sourceId)
  return `blob-${sourceId}`
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : 'Không thể hiển thị tài liệu.'
}

function useDisplayedDimensions(
  elementRef: RefObject<HTMLElement | null>,
): DisplayedPageDimensions {
  const [dimensions, setDimensions] = useState<DisplayedPageDimensions>({
    width: 0,
    height: 0,
  })

  useEffect(() => {
    const element = elementRef.current
    if (element === null) {
      return
    }

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry === undefined) {
        return
      }

      const { width, height } = entry.contentRect
      setDimensions((currentDimensions) =>
        currentDimensions.width === width && currentDimensions.height === height
          ? currentDimensions
          : { width, height },
      )
    })
    resizeObserver.observe(element)

    return () => resizeObserver.disconnect()
  }, [elementRef])

  return dimensions
}

function HighlightOverlay({
  highlight,
  dimensions,
}: {
  highlight: NormalizedBbox | undefined
  dimensions: DisplayedPageDimensions
}) {
  if (
    highlight === undefined ||
    dimensions.width === 0 ||
    dimensions.height === 0
  ) {
    return null
  }

  const rectangle = normalizedBboxToPixelRectangle(highlight, dimensions)

  return (
    <div
      className="document-viewer__highlight"
      style={rectangle}
      aria-hidden="true"
    />
  )
}

function ZoomControls({
  zoom,
  onZoomChange,
}: {
  zoom: ZoomLevel
  onZoomChange: (zoom: ZoomLevel) => void
}) {
  return (
    <div className="document-viewer__zoom" role="group" aria-label="Điều khiển thu phóng">
      <button
        type="button"
        className="document-viewer__button"
        onClick={() => onZoomChange(1)}
        disabled={zoom === 1}
      >
        Zoom out
      </button>
      <span aria-live="polite">{Math.round(zoom * 100)}%</span>
      <button
        type="button"
        className="document-viewer__button"
        onClick={() => onZoomChange(1.5)}
        disabled={zoom === 1.5}
      >
        Zoom in
      </button>
    </div>
  )
}

function PdfViewer({
  source,
  highlight,
  zoom,
  onZoomChange,
  label = 'Tài liệu PDF',
}: Extract<DocumentViewerProps, { documentType: 'pdf' }> & {
  zoom: ZoomLevel
  onZoomChange: (zoom: ZoomLevel) => void
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const displayedDimensions = useDisplayedDimensions(canvasRef)
  const [pdfDocument, setPdfDocument] = useState<PDFDocumentProxy | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [isRendering, setIsRendering] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let isActive = true
    let loadingTask: PDFDocumentLoadingTask | null = null

    async function loadPdf() {
      setLoadState('loading')
      setErrorMessage(null)
      setPdfDocument(null)
      setCurrentPage(1)
      setTotalPages(0)

      try {
        const parameters =
          typeof source === 'string'
            ? { url: source }
            : { data: await source.arrayBuffer() }

        if (!isActive) {
          return
        }

        loadingTask = getDocument(parameters)
        const loadedDocument = await loadingTask.promise

        if (!isActive) {
          await loadingTask.destroy()
          return
        }

        setPdfDocument(loadedDocument)
        setTotalPages(loadedDocument.numPages)
        setLoadState('loaded')
      } catch (error: unknown) {
        if (isActive) {
          setLoadState('error')
          setErrorMessage(getErrorMessage(error))
        }
      }
    }

    void loadPdf()

    return () => {
      isActive = false
      if (loadingTask !== null) {
        void loadingTask.destroy().catch(() => undefined)
      }
    }
  }, [source])

  useEffect(() => {
    if (pdfDocument === null || totalPages === 0) {
      return
    }

    let isActive = true
    let renderTask: RenderTask | null = null

    async function renderPage() {
      setIsRendering(true)
      setErrorMessage(null)

      try {
        const page = await pdfDocument!.getPage(currentPage)
        if (!isActive) {
          return
        }

        const canvas = canvasRef.current
        if (canvas === null) {
          throw new Error('Không tìm thấy canvas để hiển thị PDF.')
        }

        const viewport = page.getViewport({ scale: zoom })
        canvas.width = Math.ceil(viewport.width)
        canvas.height = Math.ceil(viewport.height)

        renderTask = page.render({ canvas, viewport })
        await renderTask.promise

        if (isActive) {
          setIsRendering(false)
        }
      } catch (error: unknown) {
        if (!isActive || error instanceof RenderingCancelledException) {
          return
        }

        setIsRendering(false)
        setErrorMessage(getErrorMessage(error))
      }
    }

    void renderPage()

    return () => {
      isActive = false
      renderTask?.cancel()
    }
  }, [currentPage, pdfDocument, totalPages, zoom])

  const isLoading = loadState === 'loading' || isRendering
  const showDocument =
    loadState === 'loaded' && !isRendering && errorMessage === null

  return (
    <section className="document-viewer" aria-label={label}>
      <div className="document-viewer__stage">
        {isLoading ? (
          <p className="document-viewer__message" role="status">
            Đang tải tài liệu...
          </p>
        ) : null}
        {errorMessage !== null ? (
          <p className="document-viewer__message document-viewer__message--error" role="alert">
            {errorMessage}
          </p>
        ) : null}
        <div className="document-viewer__surface">
          <canvas
            ref={canvasRef}
            className="document-viewer__canvas"
            hidden={!showDocument}
          />
          {showDocument ? (
            <HighlightOverlay
              highlight={highlight}
              dimensions={displayedDimensions}
            />
          ) : null}
        </div>
      </div>

      {loadState === 'loaded' && totalPages > 0 ? (
        <div className="document-viewer__controls">
          <nav className="document-viewer__navigation" aria-label="Điều hướng trang PDF">
            <button
              type="button"
              className="document-viewer__button"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </button>
            <span aria-live="polite">
              Trang {currentPage} / {totalPages}
            </span>
            <button
              type="button"
              className="document-viewer__button"
              onClick={() =>
                setCurrentPage((page) => Math.min(totalPages, page + 1))
              }
              disabled={currentPage === totalPages}
            >
              Next
            </button>
          </nav>
          <ZoomControls zoom={zoom} onZoomChange={onZoomChange} />
        </div>
      ) : null}
    </section>
  )
}

function ImageViewer({
  source,
  alt,
  highlight,
  zoom,
  onZoomChange,
}: Extract<DocumentViewerProps, { documentType: 'image' }> & {
  zoom: ZoomLevel
  onZoomChange: (zoom: ZoomLevel) => void
}) {
  const imageRef = useRef<HTMLImageElement>(null)
  const displayedDimensions = useDisplayedDimensions(imageRef)
  const [imageUrl] = useState(() =>
    typeof source === 'string' ? source : URL.createObjectURL(source),
  )
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [naturalWidth, setNaturalWidth] = useState(0)

  useEffect(() => {
    if (typeof source === 'string') {
      return
    }

    return () => URL.revokeObjectURL(imageUrl)
  }, [imageUrl, source])

  return (
    <section className="document-viewer" aria-label={alt}>
      <div className="document-viewer__stage">
        {loadState === 'loading' ? (
          <p className="document-viewer__message" role="status">
            Đang tải tài liệu...
          </p>
        ) : null}
        {loadState === 'error' ? (
          <p className="document-viewer__message document-viewer__message--error" role="alert">
            Không thể hiển thị ảnh.
          </p>
        ) : null}
        <div className="document-viewer__surface">
          <img
            ref={imageRef}
            className="document-viewer__image"
            src={imageUrl}
            alt={alt}
            hidden={loadState !== 'loaded'}
            style={
              naturalWidth > 0 ? { width: `${naturalWidth * zoom}px` } : undefined
            }
            onLoad={(event) => {
              setNaturalWidth(event.currentTarget.naturalWidth)
              setLoadState('loaded')
            }}
            onError={() => setLoadState('error')}
          />
          {loadState === 'loaded' ? (
            <HighlightOverlay
              highlight={highlight}
              dimensions={displayedDimensions}
            />
          ) : null}
        </div>
      </div>

      {loadState === 'loaded' ? (
        <div className="document-viewer__controls">
          <ZoomControls zoom={zoom} onZoomChange={onZoomChange} />
        </div>
      ) : null}
    </section>
  )
}

export function DocumentViewer(props: DocumentViewerProps) {
  const [zoom, setZoom] = useState<ZoomLevel>(1)

  return props.documentType === 'pdf' ? (
    <PdfViewer {...props} zoom={zoom} onZoomChange={setZoom} />
  ) : (
    <ImageViewer
      key={getImageSourceKey(props.source)}
      {...props}
      zoom={zoom}
      onZoomChange={setZoom}
    />
  )
}
