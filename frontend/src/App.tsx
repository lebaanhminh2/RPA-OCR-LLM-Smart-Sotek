import { CaseUploadPage } from './pages/CaseUploadPage'
import { ReviewPage } from './pages/ReviewPage'

function App() {
  const requestedCaseId = new URLSearchParams(window.location.search).get(
    'case_id',
  )
  const useHostedDemo =
    requestedCaseId === null &&
    (import.meta.env.VITE_DEMO_MODE === 'true' ||
      window.location.hostname.endsWith('.vercel.app'))
  return requestedCaseId === null || requestedCaseId === '' ? (
    <CaseUploadPage isDemoMode={useHostedDemo} />
  ) : (
    <ReviewPage caseId={requestedCaseId} />
  )
}

export default App
