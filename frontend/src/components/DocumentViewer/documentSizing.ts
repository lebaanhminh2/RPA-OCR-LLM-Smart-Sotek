export function fitDocumentScale(
  naturalWidth: number,
  availableWidth: number,
  zoom: number,
): number {
  if (
    !Number.isFinite(naturalWidth) ||
    !Number.isFinite(availableWidth) ||
    !Number.isFinite(zoom) ||
    naturalWidth <= 0 ||
    availableWidth <= 0 ||
    zoom <= 0
  ) {
    throw new RangeError('Document dimensions and zoom must be positive.')
  }

  return Math.min(1, availableWidth / naturalWidth) * zoom
}
