import { version as pdfjsVersion } from 'pdfjs-dist'

function App() {
  return (
    <main data-pdfjs-version={pdfjsVersion}>
      <h1>Hello</h1>
    </main>
  )
}

export default App
