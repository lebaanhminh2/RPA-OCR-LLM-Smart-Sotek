import { describe, expect, it } from 'vitest'

import { DEMO_CASE_ID } from '../api/client'
import {
  DEMO_DOCUMENTS,
  getDemoReviewUrl,
  getNextDemoStage,
} from './demoWorkflow'

describe('hosted demo workflow', () => {
  it('loads exactly the four required sample documents', () => {
    expect(DEMO_DOCUMENTS.map((document) => document.type)).toEqual([
      'CCCD_FRONT',
      'CCCD_BACK',
      'LOAN_APPLICATION',
      'LABOR_CONTRACT',
    ])
  })

  it('moves from an empty case to processing', () => {
    expect(getNextDemoStage('empty')).toBe('ready')
    expect(getNextDemoStage('ready')).toBe('processing')
  })

  it('opens the static review case after processing', () => {
    expect(getDemoReviewUrl()).toBe(`/?case_id=${DEMO_CASE_ID}`)
  })
})
