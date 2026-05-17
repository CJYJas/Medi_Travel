function ThinkingPanel({ data, expanded, onToggle, labels }) {
  if (!data) {
    return null
  }

  const algorithmSteps =
    data.algorithm_steps ||
    (data.steps || []).map((step) =>
      typeof step === 'string' ? step : `${step.label}: ${step.detail}`
    )
  const dataSources = data.data_sources || []
  const caseSignals = data.case_signals || data.inputs || null

  return (
    <aside className="thinking-aside" aria-label={labels['thinking.title']}>
      <div className="thinking-panel">
        <h3>{data.title || labels['thinking.title']}</h3>
        {data.subtitle && <p className="thinking-sub">{data.subtitle}</p>}
        <button type="button" className="thinking-toggle" onClick={onToggle}>
          <span>{expanded ? labels['thinking.hide'] : labels['thinking.show']}</span>
          <span aria-hidden="true">{expanded ? '▾' : '▸'}</span>
        </button>
        {expanded && (
          <>
            {caseSignals && Object.keys(caseSignals).length > 0 && (
              <>
                <div className="thinking-section-title">{labels['thinking.signals']}</div>
                <div className="thinking-kv">
                  {Object.entries(caseSignals).map(([key, value]) =>
                    value == null || value === '' ? null : (
                      <div key={key}>
                        <span>{key.replace(/_/g, ' ')}: </span>
                        {Array.isArray(value) ? value.join(', ') : String(value)}
                      </div>
                    )
                  )}
                </div>
              </>
            )}
            {data.engine_note && (
              <>
                <div className="thinking-section-title">Logistics</div>
                <p className="thinking-sub thinking-inline-sub">{data.engine_note}</p>
              </>
            )}
            {data.option_sources?.length > 0 && (
              <>
                <div className="thinking-section-title">{labels['badge.source']}</div>
                <div className="signal-chips">
                  {data.option_sources.map((source) => (
                    <span key={source} className="signal-chip muted">
                      {source}
                    </span>
                  ))}
                </div>
              </>
            )}
            {algorithmSteps.length > 0 && (
              <>
                <div className="thinking-section-title">{labels['thinking.steps']}</div>
                <ol className="thinking-list">
                  {algorithmSteps.map((line, index) => (
                    <li key={index}>{line}</li>
                  ))}
                </ol>
              </>
            )}
            {dataSources.length > 0 && (
              <>
                <div className="thinking-section-title">{labels['thinking.sources']}</div>
                <ul className="thinking-list">
                  {dataSources.map((source, index) => (
                    <li key={index}>{source}</li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>
    </aside>
  )
}

export default ThinkingPanel
