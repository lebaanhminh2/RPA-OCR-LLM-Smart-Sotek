import { DEMO_CASE_ID } from '../api/client'

export type DemoStage = 'empty' | 'ready' | 'processing'

export const DEMO_PROCESSING_DELAY_MS = 2_500

export const DEMO_DOCUMENTS = [
  { label: 'CCCD mặt trước', type: 'CCCD_FRONT', pages: 1 },
  { label: 'CCCD mặt sau', type: 'CCCD_BACK', pages: 1 },
  { label: 'Giấy đề nghị vay vốn', type: 'LOAN_APPLICATION', pages: 4 },
  { label: 'Hợp đồng lao động', type: 'LABOR_CONTRACT', pages: 2 },
] as const

export function getNextDemoStage(stage: DemoStage): DemoStage {
  if (stage === 'empty') {
    return 'ready'
  }
  return 'processing'
}

export function getDemoReviewUrl(): string {
  return `/?case_id=${encodeURIComponent(DEMO_CASE_ID)}`
}
