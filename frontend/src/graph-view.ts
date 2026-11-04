import type { Connection, DocumentSummary } from './api'

export function layoutDocuments(documents: DocumentSummary[]) {
  const count = documents.length
  return documents.map((document, index) => {
    let x = 320
    let y = 200
    if (count === 2) {
      x = index === 0 ? 205 : 435
    } else if (count > 2) {
      // Small collections stay compact. Larger ones need space between numbered nodes.
      const angle = (index / count) * 2 * Math.PI - Math.PI / 2
      x += (count <= 4 ? 165 : 220) * Math.cos(angle)
      y += (count <= 4 ? 105 : 145) * Math.sin(angle)
    }
    return { ...document, x, y }
  })
}

export function filterConnections(connections: Connection[], threshold: number) {
  // Match the two-decimal score shown in the interface, including scores very close to 1.
  return connections.filter((connection) => Number(connection.score.toFixed(2)) >= threshold)
}
