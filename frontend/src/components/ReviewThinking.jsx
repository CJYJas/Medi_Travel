function ReviewThinking({ labels, transparency }) {
  const completedBlocks = [
    transparency.extract,
    transparency.hospitals,
    transparency.flights,
    transparency.charities,
  ].filter(Boolean)

  if (!completedBlocks.length) {
    return <p className="thinking-sub">{labels['thinking.none']}</p>
  }

  return completedBlocks.map((block, index) => (
    <div key={index} className="thinking-mini">
      <h4>{block.title}</h4>
      <p>{block.subtitle}</p>
    </div>
  ))
}

export default ReviewThinking
