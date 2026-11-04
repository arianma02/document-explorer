import assert from 'node:assert/strict'
import { afterEach, mock, test } from 'node:test'
import { deleteDocument, getFileError, getGraph, uploadDocument } from '../src/api.ts'

afterEach(() => mock.restoreAll())

test('requests nonnegative graph matches for local slider filtering', async () => {
  const graph = { nodes: [{ id: 1, filename: 'solar.pdf' }], edges: [] }
  mock.method(globalThis, 'fetch', async (url) => {
    assert.equal(url, '/api/graph?min_similarity=0')
    return Response.json(graph)
  })
  assert.deepEqual(await getGraph(), graph)
})

test('uploads the selected file as multipart form data', async () => {
  const file = new File(['Solar energy'], 'solar.txt', { type: 'text/plain' })
  const document = { id: 1, filename: 'solar.txt' }
  mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/documents')
    assert.equal(options.method, 'POST')
    assert.equal(options.body.get('file').name, file.name)
    assert.equal(await options.body.get('file').text(), 'Solar energy')
    assert.equal(options.headers, undefined)
    return Response.json(document, { status: 201 })
  })
  assert.deepEqual(await uploadDocument(file), document)
})

test('preserves readable backend validation errors', async () => {
  mock.method(globalThis, 'fetch', async () =>
    Response.json({ detail: 'No readable text found in this PDF.' }, { status: 422 }),
  )
  await assert.rejects(getGraph(), /No readable text found in this PDF/)
})

test('handles a proxy error that returns HTML instead of JSON', async () => {
  mock.method(
    globalThis,
    'fetch',
    async () => new Response('<html>Unavailable</html>', { status: 502 }),
  )
  await assert.rejects(getGraph(), /service is temporarily unavailable/)
})

test('rejects empty, oversized and unsupported files before a request', async () => {
  const fetch = mock.method(globalThis, 'fetch', async () => {
    throw new Error('Unexpected request')
  })
  const files = [
    [new File([], 'empty.txt'), /empty/],
    [new File(['data'], 'paper.pdf.exe'), /PDF or UTF-8/],
    [new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'big.pdf'), /2 MiB/],
  ]
  for (const [file, message] of files) await assert.rejects(uploadDocument(file), message)
  assert.equal(fetch.mock.callCount(), 0)
  assert.equal(getFileError(new File(['text'], 'PAPER.PDF')), '')
  assert.equal(getFileError(new File([new Uint8Array(2 * 1024 * 1024)], 'limit.txt')), '')
})

test('gives a useful message when the collection cannot be reached', async () => {
  mock.method(globalThis, 'fetch', async () => {
    throw new TypeError('Failed to fetch')
  })
  await assert.rejects(getGraph(), /Cannot reach the server.*Refresh/)
})

test('warns against duplicate uploads when the response is lost', async () => {
  mock.method(globalThis, 'fetch', async () => {
    throw new TypeError('Failed to fetch')
  })
  await assert.rejects(uploadDocument(new File(['text'], 'paper.txt')), /may have been saved/)
})

test('handles successful responses that contain HTML or an unexpected collection', async () => {
  mock.method(globalThis, 'fetch', async () => new Response('<html>Wrong service</html>'))
  await assert.rejects(getGraph(), /unreadable response/)
  mock.restoreAll()
  mock.method(globalThis, 'fetch', async () => Response.json({ message: 'Wrong service' }))
  await assert.rejects(getGraph(), /unexpected collection/)
})

test('does not treat an invalid upload response as confirmed success', async () => {
  mock.method(globalThis, 'fetch', async () => Response.json({}))
  await assert.rejects(uploadDocument(new File(['text'], 'paper.txt')), /may have been saved/)
})

test('an empty upload response gives recovery advice instead of a JavaScript error', async () => {
  mock.method(globalThis, 'fetch', async () => new Response(null, { status: 204 }))
  await assert.rejects(uploadDocument(new File(['text'], 'paper.txt')), /may have been saved/)
})

test('cancellation is not reported as a network failure', async () => {
  const controller = new AbortController()
  controller.abort()
  const fetch = mock.method(globalThis, 'fetch', async () =>
    Response.json({ nodes: [], edges: [] }),
  )
  await assert.rejects(getGraph(controller.signal), { name: 'AbortError' })
  assert.equal(fetch.mock.callCount(), 0)
})

test('a timeout explains the retry action without waiting indefinitely', async () => {
  mock.method(AbortSignal, 'timeout', () =>
    AbortSignal.abort(new DOMException('Timed out', 'TimeoutError')),
  )
  await assert.rejects(getGraph(), /took too long.*Refresh/)
})

test('handles structured validation details without showing an object', async () => {
  mock.method(globalThis, 'fetch', async () =>
    Response.json({ detail: [{ msg: 'Invalid value' }] }, { status: 422 }),
  )
  await assert.rejects(getGraph(), /Request failed \(422\)/)
})

test('deletes by document ID and accepts an empty 204 response', async () => {
  mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/documents/7')
    assert.equal(options.method, 'DELETE')
    return new Response(null, { status: 204 })
  })
  assert.equal(await deleteDocument(7), undefined)
})

test('treats an already-deleted document as removed', async () => {
  mock.method(globalThis, 'fetch', async () =>
    Response.json({ detail: 'Document not found.' }, { status: 404 }),
  )
  assert.equal(await deleteDocument(7), undefined)
})

test('a lost delete response tells the user to refresh and check the result', async () => {
  mock.method(globalThis, 'fetch', async () => {
    throw new TypeError('Failed to fetch')
  })
  await assert.rejects(deleteDocument(7), /check whether the document was deleted/)
})
