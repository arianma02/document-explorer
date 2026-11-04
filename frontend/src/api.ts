export type DocumentSummary = {
  id: number
  filename: string
  created_at: string
}

// Vite forwards /api to FastAPI locally. Deployment can use VITE_API_URL instead.
const apiUrl = import.meta.env.VITE_API_URL || '/api'

async function readResponse(response: Response) {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : `Request failed (${response.status}). Please try again.`,
    )
  }
  return response.json()
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const response = await fetch(`${apiUrl}/documents`)
  return readResponse(response)
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${apiUrl}/documents`, {
    method: 'POST',
    body: form,
  })
  return readResponse(response)
}
