function Stepper({ labels, currentStep }) {
  const stepDefinitions = [
    { number: 1, label: labels['stepper.1'] },
    { number: 2, label: labels['stepper.2'] },
    { number: 3, label: labels['stepper.3'] },
    { number: 4, label: labels['stepper.4'] },
    { number: 5, label: labels['stepper.5'] },
  ]

  return (
    <nav className="stepper" aria-label="Progress">
      {stepDefinitions.map((stepDefinition, index) => {
        const stepStatus =
          currentStep > stepDefinition.number
            ? 'done'
            : currentStep === stepDefinition.number
              ? 'active'
              : ''

        return (
          <span key={stepDefinition.number}>
            {index > 0 && <span className="stepper-sep">/</span>}
            <span className={`stepper-step ${stepStatus}`}>
              <span className="stepper-num">{stepDefinition.number}</span>
              {stepDefinition.label}
            </span>
          </span>
        )
      })}
    </nav>
  )
}

export default Stepper
