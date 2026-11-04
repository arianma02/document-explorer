export type DocumentSummary = {
  id: number
  filename: string
  created_at: string
}

export type Passage = {
  id: number
  document_id: number
  position: number
  page_number: number | null
  text: string
}

export type Connection = {
  source: number
  target: number
  score: number
  source_passage: Passage
  target_passage: Passage
}

export type DocumentGraph = {
  nodes: DocumentSummary[]
  edges: Connection[]
}

// Vite forwards /api to FastAPI locally. Deployment can use VITE_API_URL instead.
const apiUrl = (import.meta.env?.VITE_API_URL || '/api').replace(/\/+$/, '')

async function request(path: string, options: RequestInit = {}) {
  const timeout = AbortSignal.timeout(120_000)
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout
  let retryAdvice = 'Try Refresh in a moment.'
  if (options.method === 'POST') {
    retryAdvice = 'Refresh the collection before uploading again, as the file may have been saved.'
  } else if (options.method === 'DELETE') {
    retryAdvice = 'Refresh the collection to check whether the document was deleted.'
  }
  let response: Response
  try {
    signal.throwIfAborted()
    response = await fetch(`${apiUrl}${path}`, { ...options, signal })
  } catch (error) {
    if (options.signal?.aborted) throw error
    throw new Error(
      `${signal.aborted ? 'The server took too long to respond.' : 'Cannot reach the server.'} ${retryAdvice}`,
    )
  }
  // Deleting an already-removed document also fulfils the user's request.
  if (response.status === 204 || (options.method === 'DELETE' && response.status === 404)) return
  const body = await response.json().catch(() => null)
  if (options.signal?.aborted) throw options.signal.reason
  if (!response.ok) {
    if (response.status >= 500) {
      throw new Error(`The service is temporarily unavailable. ${retryAdvice}`)
    }
    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : `Request failed (${response.status}). Please try again.`,
    )
  }
  if (body === null) {
    throw new Error(`The server returned an unreadable response. ${retryAdvice}`)
  }
  return body
}

export async function getGraph(signal?: AbortSignal): Promise<DocumentGraph> {
  // Load nonnegative matches once so the slider can filter without more requests.
  const graph = await request('/graph?min_similarity=0', { signal })
  if (!graph || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges)) {
    throw new Error('The server returned an unexpected collection. Try Refresh in a moment.')
  }
  return graph
}

export async function deleteDocument(documentId: number): Promise<void> {
  await request(`/documents/${documentId}`, { method: 'DELETE' })
}

export function getFileError(file: File): string {
  if (!/\.(pdf|txt)$/i.test(file.name)) return 'Choose a PDF or UTF-8 text file.'
  if (file.size === 0) return 'This file is empty. Choose a file containing text.'
  if (file.size > 2 * 1024 * 1024) return 'The document must be 2 MiB or smaller.'
  return ''
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const error = getFileError(file)
  if (error) throw new Error(error)
  const form = new FormData()
  form.append('file', file)
  const document = await request('/documents', {
    method: 'POST',
    body: form,
  })
  if (!document || !Number.isSafeInteger(document.id) || typeof document.filename !== 'string') {
    throw new Error(
      'Could not confirm the upload. Refresh the collection before uploading again, as the file may have been saved.',
    )
  }
  return document
}
