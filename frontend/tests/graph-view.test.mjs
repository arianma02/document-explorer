import assert from 'node:assert/strict'
import { test } from 'node:test'
import { filterConnections, layoutDocuments } from '../src/graph-view.ts'

function documents(count) {
  return Array.from({ length: count }, (_, index) => ({
    id: index + 1,
    filename: `Document ${index + 1}.pdf`,
    created_at: '2026-11-04T12:00:00Z',
  }))
}

test('zero and one document have sensible layouts without invalid coordinates', () => {
  assert.deepEqual(layoutDocuments([]), [])
  const [node] = layoutDocuments(documents(1))
  assert.ok(node.x > 250 && node.x < 390)
  assert.ok(node.y > 150 && node.y < 260)
})

test('two documents sit side by side with labels below the connecting line', () => {
  const nodes = layoutDocuments(documents(2))
  assert.equal(nodes[0].y, nodes[1].y)
  assert.ok(nodes[1].x - nodes[0].x >= 150)
  assert.ok(nodes[1].x - nodes[0].x <= 300)
})

test('all supported collection sizes fit and their circles do not overlap', () => {
  for (let count = 2; count <= 20; count++) {
    const source = documents(count)
    const nodes = layoutDocuments(source)
    assert.deepEqual(
      nodes.map((node) => node.id),
      source.map((node) => node.id),
    )
    for (const [index, node] of nodes.entries()) {
      assert.ok(node.x >= 25 && node.x <= 615)
      assert.ok(node.y >= 25 && node.y <= 395)
      for (const other of nodes.slice(index + 1)) {
        assert.ok(Math.hypot(node.x - other.x, node.y - other.y) > 44)
      }
    }
  }
})

test('filtering agrees with displayed score rounding at threshold boundaries', () => {
  const connections = [{ score: 0.49999 }, { score: 0.48 }, { score: 0.9999999999 }]
  assert.deepEqual(filterConnections(connections, 0.5), [connections[0], connections[2]])
  assert.deepEqual(filterConnections(connections, 1), [connections[2]])
  assert.deepEqual(filterConnections([], 0), [])
})
