import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { deleteDocument, getFileError, getGraph, uploadDocument } from './api'
import type { DocumentGraph } from './api'
import Graph from './Graph'

export default function App() {
  const [graph, setGraph] = useState<DocumentGraph | null>(null)
  const documents = graph?.nodes ?? []
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const deleteTrigger = useRef<HTMLButtonElement | null>(null)
  const cancelDeleteButton = useRef<HTMLButtonElement>(null)
  const [loadError, setLoadError] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [message, setMessage] = useState('')
  const fileError = file ? getFileError(file) : ''
  const uploadProblem = fileError || uploadError
  const initialLoading = loading && !graph && !loadError
  const busy = loading || uploading || deleting
  const deleteTarget = documents.find((document) => document.id === pendingDeleteId)
  let collectionStatus = 'Collection unavailable'
  if (graph) collectionStatus = `${documents.length} of 20 documents`
  else if (initialLoading) collectionStatus = 'Loading collection…'

  function loadGraph(signal?: AbortSignal) {
    return getGraph(signal)
      .then((result) => {
        if (signal?.aborted) return false
        setGraph(result)
        setLoadError('')
        return true
      })
      .catch((error) => {
        if (signal?.aborted) return false
        setLoadError(
          error instanceof Error ? error.message : 'Could not load the collection. Please retry.',
        )
        return false
      })
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }

  useEffect(() => {
    const controller = new AbortController()
    void loadGraph(controller.signal)
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (pendingDeleteId !== null) cancelDeleteButton.current?.focus()
  }, [pendingDeleteId])

  function cancelDelete() {
    setPendingDeleteId(null)
    setDeleteError('')
    deleteTrigger.current?.focus()
  }

  function refreshCollection() {
    if (busy) return
    setLoading(true)
    void loadGraph()
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    // Keep the form element because event.currentTarget is cleared before the upload finishes.
    const form = event.currentTarget
    if (!file || busy || fileError) return
    setUploadError('')
    setMessage('')
    setUploading(true)
    try {
      const document = await uploadDocument(file)
      setMessage(`${document.filename} uploaded and processed.`)
      setFile(null)
      form.reset()
      setLoading(true)
      const refreshed = await loadGraph()
      if (!refreshed) {
        setLoadError(
          'Your upload was saved, but the collection could not be refreshed. Retry loading below. Do not upload the file again.',
        )
      }
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete() {
    if (!deleteTarget || busy) return
    const documentId = deleteTarget.id
    const filename = deleteTarget.filename
    setDeleting(true)
    setDeleteError('')
    setMessage('')
    try {
      await deleteDocument(documentId)
      // Remove confirmed deletions immediately, even if the following refresh fails.
      setGraph(
        (current) =>
          current && {
            nodes: current.nodes.filter((document) => document.id !== documentId),
            edges: current.edges.filter(
              (edge) => edge.source !== documentId && edge.target !== documentId,
            ),
          },
      )
      setPendingDeleteId(null)
      setMessage(`${filename} deleted.`)
      setLoading(true)
      const refreshed = await loadGraph()
      if (!refreshed)
        setLoadError(
          'The document was deleted, but the collection could not be refreshed. Retry loading.',
        )
    } catch (error) {
      setDeleteError(
        error instanceof Error ? error.message : 'Could not delete the document. Please try again.',
      )
    } finally {
      setDeleting(false)
    }
  }

  return (
    <main>
      <header className="page-header">
        <div className="intro">
          <div className="app-brand">
            <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
              <path d="M7 7 21 14 7 21Z" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="7" cy="7" r="3" fill="currentColor" />
              <circle cx="21" cy="14" r="3" fill="currentColor" />
              <circle cx="7" cy="21" r="3" fill="currentColor" />
            </svg>
            <h1>Document Explorer</h1>
          </div>
          <p>Explore documents through their connections.</p>
        </div>
        <p className="header-note">{collectionStatus}</p>
      </header>

      {loadError && (
        <div className="error load-error" role="alert">
          <p>
            {loadError} {graph && 'Showing the last loaded collection.'}
          </p>
          <button
            className="secondary refresh-button"
            onClick={refreshCollection}
            aria-busy={loading}
            disabled={busy}
          >
            Retry loading
          </button>
        </div>
      )}
      <div className="workspace">
        <aside className="source-panels" aria-label="Document sources">
          <section className="panel upload-panel" aria-labelledby="upload-title">
            <h2 id="upload-title">Upload document</h2>
            <p>Choose a text-based PDF or UTF-8 text file. Scanned PDFs aren’t supported.</p>
            <form onSubmit={handleUpload}>
              <label className="file-picker" htmlFor="document-file">
                <span className="picker-icon" aria-hidden="true">
                  +
                </span>
                <span>{file ? file.name : 'Choose a document'}</span>
                <input
                  id="document-file"
                  type="file"
                  aria-label="Document file"
                  aria-describedby={uploadProblem ? 'file-limits upload-error' : 'file-limits'}
                  aria-invalid={Boolean(fileError)}
                  accept=".pdf,.txt"
                  required
                  disabled={uploading || deleting}
                  onChange={(event) => {
                    setFile(event.target.files?.[0] ?? null)
                    setMessage('')
                    setUploadError('')
                  }}
                />
              </label>
              <p id="file-limits" className="file-hint">
                Up to 2 MiB · 100 passages per document
              </p>
              <button type="submit" disabled={!file || busy || Boolean(fileError)}>
                {uploading ? 'Processing document…' : 'Upload document'}
              </button>
              {uploading && (
                <output>Extracting text and preparing passage comparisons. Please wait.</output>
              )}
            </form>
            {uploadProblem && (
              <p id="upload-error" className="error" role="alert">
                {uploadProblem}
              </p>
            )}
            {message && <output className="success">{message}</output>}
          </section>

          <section className="panel collection-panel" aria-labelledby="collection-title">
            <div className="collection-heading">
              <h2 id="collection-title">Documents</h2>
              <button
                className="secondary refresh-button"
                onClick={refreshCollection}
                aria-busy={loading}
                disabled={busy}
              >
                Refresh
              </button>
            </div>
            <p className="collection-description">The latest 20 uploads, newest first.</p>
            {deleteTarget && (
              <div className="delete-confirmation" aria-busy={deleting}>
                <p>
                  Delete document {documents.indexOf(deleteTarget) + 1}:{' '}
                  <strong>{deleteTarget.filename}</strong>?
                </p>
                <p>This removes its passages and connections. This cannot be undone.</p>
                {deleteError && (
                  <p className="error" role="alert">
                    {deleteError}
                  </p>
                )}
                <div className="delete-actions">
                  <button
                    className="secondary"
                    disabled={deleting}
                    ref={cancelDeleteButton}
                    onClick={cancelDelete}
                  >
                    Cancel
                  </button>
                  <button className="danger-button" disabled={busy} onClick={handleDelete}>
                    {deleting ? 'Deleting…' : 'Delete document'}
                  </button>
                </div>
              </div>
            )}
            {initialLoading ? (
              <output>Loading documents…</output>
            ) : !graph ? (
              <p className="graph-description">The document list could not be loaded.</p>
            ) : documents.length === 0 ? (
              <div className="empty-state">
                <h3>No documents yet</h3>
                <p>Upload a PDF or text file to get started.</p>
              </div>
            ) : (
              <ul className="document-list">
                {documents.map((document, index) => (
                  <li key={document.id}>
                    <span className="file-icon" aria-hidden="true">
                      {index + 1}
                    </span>
                    <div>
                      <strong>{document.filename}</strong>
                      <span>Added {new Date(document.created_at).toLocaleString()}</span>
                    </div>
                    <button
                      className="delete-document-button"
                      aria-label={`Delete document ${index + 1}: ${document.filename}`}
                      title={`Delete ${document.filename}`}
                      disabled={busy}
                      onClick={(event) => {
                        deleteTrigger.current = event.currentTarget
                        setPendingDeleteId(document.id)
                        setDeleteError('')
                      }}
                    >
                      <svg
                        width="17"
                        height="17"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        aria-hidden="true"
                      >
                        <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 10v7M14 10v7" />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
        {graph ? (
          <Graph graph={graph} />
        ) : (
          <section className="load-state" aria-busy={loading}>
            {initialLoading ? (
              <output>Loading documents and connections…</output>
            ) : (
              <>
                <h2>Connection map unavailable</h2>
                <p>Retry loading the collection to display your documents and connections.</p>
              </>
            )}
          </section>
        )}
      </div>
    </main>
  )
}
