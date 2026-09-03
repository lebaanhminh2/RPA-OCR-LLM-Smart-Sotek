import { CaseUploadPage } from './pages/CaseUploadPage'
import { ReviewPage } from './pages/ReviewPage'
import { DEMO_CASE_ID } from './api/client'

function App() {
  const requestedCaseId = new URLSearchParams(window.location.search).get(
    'case_id',
  )
  const useHostedDemo =
    requestedCaseId === null &&
    (import.meta.env.VITE_DEMO_MODE === 'true' ||
      window.location.hostname.endsWith('.vercel.app'))
  const caseId = useHostedDemo ? DEMO_CASE_ID : requestedCaseId

  return caseId === null || caseId === '' ? (
    <CaseUploadPage />
  ) : (
    <ReviewPage caseId={caseId} />
  )
}

export default App
