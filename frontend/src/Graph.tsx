/* oxlint-disable jsx-a11y/prefer-tag-over-role -- SVG groups need an explicit button role. */
import { useRef, useState } from 'react'
import type { DocumentGraph } from './api'
import { filterConnections, layoutDocuments } from './graph-view'

export default function Graph({ graph }: { graph: DocumentGraph }) {
  const [threshold, setThreshold] = useState(0.5)
  const [selectedPair, setSelectedPair] = useState('')
  const evidenceRef = useRef<HTMLElement>(null)
  const edges = filterConnections(graph.edges, threshold)
  // Resolve the selection from current data so hidden or removed matches cannot stay selected.
  const selected = edges.find((edge) => `${edge.source}-${edge.target}` === selectedPair)

  const nodes = layoutDocuments(graph.nodes)

  function documentName(id: number) {
    const index = graph.nodes.findIndex((document) => document.id === id)
    return index < 0 ? 'Unknown document' : `${index + 1}. ${graph.nodes[index].filename}`
  }

  function selectConnection(pair: string) {
    setSelectedPair(pair)
    evidenceRef.current?.scrollIntoView({ block: 'nearest' })
  }

  return (
    <section className="graph-workspace" aria-labelledby="graph-title">
      <div className="graph-stage">
        <header className="graph-toolbar">
          <div>
            <h2 id="graph-title">Connection map</h2>
            <p className="graph-hint">Select a connection to inspect its source passages.</p>
          </div>
          <div className="similarity-control">
            <label htmlFor="similarity">
              Minimum similarity <strong>{threshold.toFixed(2)}</strong>
            </label>
            <input
              id="similarity"
              type="range"
              min="0"
              max="1"
              step="0.01"
              disabled={nodes.length < 2}
              value={threshold}
              onChange={(event) => setThreshold(Number(event.target.value))}
            />
          </div>
        </header>

        {nodes.length === 0 ? (
          <div className="canvas-empty">
            <h3>Your documents will appear here</h3>
            <p>Upload at least two documents to start comparing passages.</p>
          </div>
        ) : (
          <div className="graph-canvas">
            <svg
              className="document-graph"
              data-compact={nodes.length <= 4}
              viewBox={nodes.length <= 2 ? '100 110 440 220' : '0 0 640 420'}
              aria-label="Document connection graph"
            >
              <title>Connections between your documents</title>
              {edges.map((edge) => {
                const source = nodes.find((node) => node.id === edge.source)
                const target = nodes.find((node) => node.id === edge.target)
                if (!source || !target) return null
                const pair = `${edge.source}-${edge.target}`
                return (
                  <g
                    key={pair}
                    role="button"
                    tabIndex={0}
                    className={selectedPair === pair ? 'graph-edge selected' : 'graph-edge'}
                    aria-pressed={selectedPair === pair}
                    onClick={() => selectConnection(pair)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        selectConnection(pair)
                      }
                    }}
                    aria-label={`${documentName(source.id)} and ${documentName(target.id)}, similarity ${edge.score.toFixed(2)}`}
                  >
                    <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} />
                    <circle cx={(source.x + target.x) / 2} cy={(source.y + target.y) / 2} r="8" />
                  </g>
                )
              })}
              {nodes.map((node, index) => (
                <g key={node.id} className="graph-node">
                  <title>{documentName(node.id)}</title>
                  <circle cx={node.x} cy={node.y} r="22" />
                  <text x={node.x} y={node.y} dy="0.35em" textAnchor="middle">
                    {index + 1}
                  </text>
                  {/* Keep filenames off crowded maps to avoid overlapping labels. */}
                  {nodes.length <= 6 && (
                    <text className="node-label" x={node.x} y={node.y + 42} textAnchor="middle">
                      {node.filename.length > 18 ? node.filename.slice(0, 16) + '…' : node.filename}
                    </text>
                  )}
                </g>
              ))}
            </svg>
          </div>
        )}

        <div className="canvas-footer">
          <span>
            Documents: {nodes.length} · Connections: {edges.length}
          </span>
          <span>Numbers match the document list. Position does not indicate similarity.</span>
        </div>
        <p className="graph-disclaimer">
          Scores describe related content, not probability or factual agreement.
        </p>
      </div>

      <aside className="graph-inspector" aria-label="Connection inspector">
        <div className="inspector-heading">
          <h2>Connections</h2>
          <span>{edges.length}</span>
        </div>
        {edges.length === 0 ? (
          <p className="graph-description">
            {nodes.length === 0
              ? 'Upload two documents to compare their passages.'
              : nodes.length === 1
                ? 'Upload another document to find connections.'
                : graph.edges.length > 0
                  ? `No connections reach ${threshold.toFixed(2)}. Lower the minimum similarity to see weaker matches.`
                  : 'No comparable matches are available. Try related documents, or re-upload older files to include them in passage analysis.'}
          </p>
        ) : (
          <ul className="connection-list">
            {edges.map((edge) => {
              const pair = `${edge.source}-${edge.target}`
              return (
                <li key={pair}>
                  <button
                    className="connection-button"
                    aria-pressed={selectedPair === pair}
                    onClick={() => selectConnection(pair)}
                  >
                    <span>
                      <span className="connection-filename" title={documentName(edge.source)}>
                        {documentName(edge.source)}
                      </span>
                      <span className="connection-filename" title={documentName(edge.target)}>
                        ↔ {documentName(edge.target)}
                      </span>
                    </span>
                    <strong>{edge.score.toFixed(2)}</strong>
                  </button>
                </li>
              )
            })}
          </ul>
        )}

        {edges.length > 0 && (
          <section ref={evidenceRef} className="evidence" aria-labelledby="evidence-title">
            <h3 id="evidence-title">Matching passages</h3>
            {selected ? (
              <>
                <p>Strongest passage match · {selected.score.toFixed(2)}</p>
                <div className="evidence-grid">
                  {[selected.source_passage, selected.target_passage].map((passage) => (
                    <article key={passage.id}>
                      <h4>{documentName(passage.document_id)}</h4>
                      <p className="graph-hint">
                        {passage.page_number === null ? 'Text file' : `Page ${passage.page_number}`}
                        {' · '}Passage {passage.position}
                      </p>
                      <blockquote>{passage.text}</blockquote>
                    </article>
                  ))}
                </div>
              </>
            ) : (
              <p className="graph-description">
                {selectedPair
                  ? 'The previous connection is no longer visible. Select another connection or lower the threshold.'
                  : 'Select a connection from the map or list to read both passages.'}
              </p>
            )}
          </section>
        )}
      </aside>
    </section>
  )
}
