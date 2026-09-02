import { CaseUploadPage } from './pages/CaseUploadPage'
import { ReviewPage } from './pages/ReviewPage'

function App() {
  const caseId = new URLSearchParams(window.location.search).get('case_id')

  return caseId === null || caseId === '' ? (
    <CaseUploadPage />
  ) : (
    <ReviewPage caseId={caseId} />
  )
}

export default App
