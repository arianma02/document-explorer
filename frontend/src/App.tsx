import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { listDocuments, uploadDocument } from './api'
import type { DocumentSummary } from './api'

export default function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  function loadDocuments() {
    return listDocuments()
      .then(setDocuments)
      .catch(() => {
        setError('Could not load documents. Check that the backend is running, then retry.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    void loadDocuments()
  }, [])

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    // Keep the form element because event.currentTarget is cleared before the upload finishes.
    const form = event.currentTarget
    if (!file) return
    setError('')
    setMessage('')
    if (!/\.(pdf|txt)$/i.test(file.name)) {
      setError('Choose a PDF or UTF-8 text file.')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('The document must be 2 MiB or smaller.')
      return
    }
    setUploading(true)
    try {
      const document = await uploadDocument(file)
      setDocuments((current) => [document, ...current].slice(0, 20))
      setMessage(`${document.filename} uploaded and processed.`)
      setFile(null)
      form.reset()
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <main>
      <header className="page-header">
        <span className="brand-mark" aria-hidden="true">
          ↗
        </span>
        <span>Document Explorer</span>
        <span className="header-note">Read between documents.</span>
      </header>

      <section className="intro">
        <p className="eyebrow">YOUR DOCUMENT COLLECTION</p>
        <h1>
          Bring your reading
          <br />
          into one place.
        </h1>
        <p>Upload documents to explore their connections and the passages behind them.</p>
      </section>

      <div className="workspace">
        <section className="panel upload-panel" aria-labelledby="upload-title">
          <span className="section-number">01 / ADD SOURCES</span>
          <h2 id="upload-title">Start with a document.</h2>
          <p>Choose a text-based PDF or UTF-8 text file. Scanned PDFs aren’t supported.</p>
          <form onSubmit={handleUpload}>
            <label htmlFor="document-file">Document file</label>
            <input
              id="document-file"
              type="file"
              accept=".pdf,.txt"
              required
              disabled={uploading}
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null)
                setMessage('')
              }}
            />
            <p className="file-hint">Up to 2 MiB · 100 passages per document</p>
            <button type="submit" disabled={!file || uploading || loading}>
              {uploading ? 'Processing document…' : 'Upload document'}
            </button>
            {uploading && (
              <output>Extracting text and preparing passage comparisons. Please wait.</output>
            )}
          </form>
          {message && <output className="success">{message}</output>}
        </section>

        <section className="panel collection-panel" aria-labelledby="collection-title">
          <div className="collection-heading">
            <div>
              <span className="section-number">02 / COLLECTION</span>
              <h2 id="collection-title">Your documents</h2>
            </div>
            <button
              className="secondary"
              onClick={() => {
                setLoading(true)
                setError('')
                void loadDocuments()
              }}
              disabled={loading || uploading}
            >
              {loading ? 'Loading…' : 'Refresh'}
            </button>
          </div>
          <p className="collection-description">The latest 20 uploads, newest first.</p>
          {loading ? (
            <output>Loading documents…</output>
          ) : documents.length === 0 ? (
            <div className="empty-state">
              <span aria-hidden="true">▤</span>
              <h3>Your collection starts here.</h3>
              <p>Upload your first document to get started.</p>
            </div>
          ) : (
            <ul className="document-list">
              {documents.map((document) => (
                <li key={document.id}>
                  <span className="file-icon" aria-hidden="true">
                    ▤
                  </span>
                  <div>
                    <strong>{document.filename}</strong>
                    <span>Added {new Date(document.created_at).toLocaleString()}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <footer>Follow the connection. Check the source.</footer>
    </main>
  )
}
