import { useEffect, useState } from 'react'
import './App.css'
import ThinkingPanel from './components/ThinkingPanel'
import ReviewThinking from './components/ReviewThinking'
import Stepper from './components/Stepper'
import {
  API_BASE,
  FALLBACK_RATES,
  LANGUAGE_COUNTRY_MAP,
  LANGUAGE_OPTIONS,
  UI_STRINGS,
} from './config'

function getTransparencyForStep(step, transparencyByStep) {
  if (step === 1) {
    return transparencyByStep.extract
  }
  if (step === 2 || step === 2.5) {
    return transparencyByStep.hospitals
  }
  if (step === 3) {
    return transparencyByStep.flights
  }
  if (step === 4) {
    return transparencyByStep.charities
  }
  return null
}

function buildFallbackFlight(originCountry) {
  return {
    airline: 'Mock Airlines',
    travel_cost_usd: 150,
    route: `${originCountry} to KUL`,
    departure: '10:00',
  }
}

function buildFallbackDoctor() {
  return {
    name: 'Dr. Ahmad bin Ali',
    hospital: 'Hospital Kuala Lumpur',
    specialty_tags: 'Cardiology',
  }
}

function buildFallbackCharity() {
  return { name: 'Hope Foundation', max_coverage_usd: 500 }
}

function buildHospitalMessage(selectedDoctor, selectedFlight, originCountry, condition) {
  return `Hello ${selectedDoctor?.hospital}, I am a patient from ${originCountry}. I am seeking treatment for ${condition}. I would like to consult with ${selectedDoctor?.name}. I will be arriving via ${selectedFlight?.airline}. Please advise on the next steps.`
}

function openDoctorProfileFallback(doctor) {
  const fallbackUrl = `/profile.html?name=${encodeURIComponent(doctor.name)}&hospital=${encodeURIComponent(doctor.hospital)}`
  window.open(fallbackUrl, '_blank')
}

function App() {
  const [language, setLanguage] = useState('en')
  const [translatedStrings, setTranslatedStrings] = useState({})
  const labels =
    language === 'en'
      ? UI_STRINGS
      : { ...UI_STRINGS, ...translatedStrings }

  const [step, setStep] = useState(1)
  const [currency, setCurrency] = useState('USD')
  const [originCountry, setOriginCountry] = useState('Indonesia')
  const [condition, setCondition] = useState('')
  const [medicalData, setMedicalData] = useState({})
  const [doctors, setDoctors] = useState([])
  const [selectedDoctor, setSelectedDoctor] = useState(null)
  const [flights, setFlights] = useState([])
  const [selectedFlight, setSelectedFlight] = useState(null)
  const [charities, setCharities] = useState([])
  const [selectedCharity, setSelectedCharity] = useState(null)
  const [loading, setLoading] = useState(false)
  const [doctorProfileLinks, setDoctorProfileLinks] = useState({})
  const [summaryMessage, setSummaryMessage] = useState('')
  const [dissatisfactionReason, setDissatisfactionReason] = useState('')
  const [transparencyByStep, setTransparencyByStep] = useState({
    extract: null,
    hospitals: null,
    flights: null,
    charities: null,
  })
  const [thinkingExpanded, setThinkingExpanded] = useState(true)

  const currentThinking = getTransparencyForStep(step, transparencyByStep)
  const visibleStepperStep = step === 2.5 ? 2 : step

  useEffect(() => {
    if (language === 'en') {
      return
    }

    const fetchTranslations = async () => {
      try {
        const response = await fetch(`${API_BASE}/translate-batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            texts: UI_STRINGS,
            target_language: language,
          }),
        })
        const responseData = await response.json()
        if (responseData.translated_texts) {
          setTranslatedStrings(responseData.translated_texts)
        }
      } catch (error) {
        console.error('Translation error', error)
      }
    }

    fetchTranslations()
  }, [language])

  function convertUsdPrice(usdValue) {
    if (!usdValue) {
      return 0
    }

    const exchangeRate = FALLBACK_RATES[currency] || 1
    return (parseFloat(usdValue) * exchangeRate).toLocaleString(undefined, {
      maximumFractionDigits: 0,
    })
  }

  async function handleFileUpload(event) {
    const selectedFile = event.target.files[0]
    if (!selectedFile) {
      return
    }

    setLoading(true)
    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch(`${API_BASE}/extract`, {
        method: 'POST',
        body: formData,
      })
      const responseData = await response.json()
      const extractedCondition =
        responseData.medical_data?.condition ||
        responseData.medical_data?.diagnosis ||
        'Unknown Condition'

      setCondition(extractedCondition)
      setMedicalData(responseData.medical_data || { condition: extractedCondition })
      setTransparencyByStep((previousTransparency) => ({
        ...previousTransparency,
        extract: responseData.decision_transparency || null,
      }))
    } catch (error) {
      console.error(error)
      alert('Failed to extract condition from file.')
    }

    setLoading(false)
  }

  async function handleFindDoctors() {
    if (!condition) {
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/match-hospitals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medical_data: { ...medicalData, condition },
          origin_country: originCountry,
          language,
        }),
      })
      const responseData = await response.json()
      setDoctors(responseData.hospitals || [])
      setSelectedDoctor(null)
      setTransparencyByStep((previousTransparency) => ({
        ...previousTransparency,
        hospitals: responseData.decision_transparency || null,
      }))
      setStep(2)
    } catch (error) {
      console.error(error)
      setDoctors([buildFallbackDoctor()])
      setSelectedDoctor(null)
      setTransparencyByStep((previousTransparency) => ({
        ...previousTransparency,
        hospitals: null,
      }))
      setStep(2)
    }
    setLoading(false)
  }

  async function handleRefineDoctors() {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/match-hospitals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medical_data: {
            ...medicalData,
            condition,
            dissatisfaction_reason: dissatisfactionReason,
          },
          origin_country: originCountry,
          language,
        }),
      })
      const responseData = await response.json()
      setTransparencyByStep((previousTransparency) => ({
        ...previousTransparency,
        hospitals: responseData.decision_transparency || null,
      }))

      if (responseData.hospitals && responseData.hospitals.length > 0) {
        const hospitalsUnchanged =
          JSON.stringify(responseData.hospitals) === JSON.stringify(doctors)
        if (hospitalsUnchanged) {
          alert('No other suitable options found based on your feedback.')
        } else {
          setDoctors(responseData.hospitals)
          setSelectedDoctor(null)
          alert('We found new options based on your feedback!')
        }
      } else {
        alert('No other suitable options found. Showing previous options.')
      }
      setStep(2)
    } catch (error) {
      console.error(error)
      setStep(2)
    }
    setLoading(false)
  }

  async function handleDoctorProfile(doctor, event) {
    event.stopPropagation()

    if (doctorProfileLinks[doctor.name]) {
      window.open(doctorProfileLinks[doctor.name], '_blank')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/doctor-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doctor_name: doctor.name,
          hospital_name: doctor.hospital,
        }),
      })
      const responseData = await response.json()

      if (responseData.profile_url) {
        setDoctorProfileLinks((previousLinks) => ({
          ...previousLinks,
          [doctor.name]: responseData.profile_url,
        }))
        window.open(responseData.profile_url, '_blank')
      } else {
        openDoctorProfileFallback(doctor)
      }
    } catch (error) {
      console.error(error)
      openDoctorProfileFallback(doctor)
    }

    setLoading(false)
  }

  async function handleFindFlights() {
    if (!selectedDoctor) {
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/match-flights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medical_data: { condition },
          origin_country: originCountry,
          language,
        }),
      })
      const responseData = await response.json()
      const flightOptions = responseData.flight_options?.options || responseData.flight_options || []

      setFlights(flightOptions.length > 0 ? flightOptions : [buildFallbackFlight(originCountry)])
      setSelectedFlight(null)
      setTransparencyByStep((previousTransparency) => ({
        ...previousTransparency,
        flights: responseData.decision_transparency || null,
      }))
      setStep(3)
    } catch (error) {
      console.error(error)
      setFlights([buildFallbackFlight(originCountry)])
      setSelectedFlight(null)
      setTransparencyByStep((previousTransparency) => ({
        ...previousTransparency,
        flights: null,
      }))
      setStep(3)
    }
    setLoading(false)
  }

  async function handleFindCharities() {
    if (!selectedFlight) {
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/match-charities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medical_data: { condition },
          origin_country: originCountry,
          language,
        }),
      })
      const responseData = await response.json()

      setCharities(responseData.charities || [])
      setSelectedCharity(null)
      setTransparencyByStep((previousTransparency) => ({
        ...previousTransparency,
        charities: responseData.decision_transparency || null,
      }))
      setStep(4)
    } catch (error) {
      console.error(error)
      setCharities([buildFallbackCharity()])
      setSelectedCharity(null)
      setTransparencyByStep((previousTransparency) => ({
        ...previousTransparency,
        charities: null,
      }))
      setStep(4)
    }
    setLoading(false)
  }

  async function generateSummary() {
    const hospitalMessage = buildHospitalMessage(
      selectedDoctor,
      selectedFlight,
      originCountry,
      condition
    )

    if (language === 'en') {
      setSummaryMessage(hospitalMessage)
      setStep(5)
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/translate-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: hospitalMessage,
          target_language: language,
        }),
      })
      const responseData = await response.json()
      setSummaryMessage(responseData.translated_text || hospitalMessage)
    } catch (error) {
      console.error(error)
      setSummaryMessage(hospitalMessage)
    }
    setStep(5)
    setLoading(false)
  }

  async function handleGenerateLetter(templateKey = 'mhtc_visa_support') {
    setLoading(true)
    try {
      const selectedCharityPayload = selectedCharity === 'NONE' ? null : selectedCharity
      const response = await fetch(`${API_BASE}/generate-letter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_key: templateKey,
          user_data: {
            patient_name: 'Patient',
            current_date: new Date().toLocaleDateString(),
          },
          medical_data: { condition },
          package_data: {
            specialist: selectedDoctor,
            flight: selectedFlight,
            charity: selectedCharityPayload,
          },
          target_language: language,
        }),
      })

      if (response.ok) {
        const pdfBlob = await response.blob()
        const objectUrl = window.URL.createObjectURL(pdfBlob)
        const downloadAnchor = document.createElement('a')
        downloadAnchor.href = objectUrl
        downloadAnchor.download = `${templateKey}_${language}.pdf`
        downloadAnchor.click()
      } else {
        alert('Backend failed to generate letter. Check terminal for error.')
      }
    } catch (error) {
      console.error(error)
      alert('Failed to generate letter')
    }
    setLoading(false)
  }

  function handleLanguageChange(event) {
    const nextLanguage = event.target.value
    setLanguage(nextLanguage)

    const mappedCountry = LANGUAGE_COUNTRY_MAP[nextLanguage]
    if (mappedCountry) {
      setOriginCountry(mappedCountry)
    }
  }

  function renderStepOne() {
    return (
      <div className="step">
        <h2>{labels['step.1.title']}</h2>
        <div className="form-group">
          <label htmlFor="origin">{labels['step.1.origin']}</label>
          <input
            id="origin"
            type="text"
            className="input-large"
            value={originCountry}
            onChange={(event) => setOriginCountry(event.target.value)}
          />
        </div>
        <div className="form-group">
          <label htmlFor="chart">{labels['step.1.upload']}</label>
          <div className="file-upload-wrapper">
            <button type="button" className="btn-upload">
              Choose file (PDF or image)
            </button>
            <input id="chart" type="file" accept=".pdf,image/*" onChange={handleFileUpload} />
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="condition">{labels['step.1.condition']}</label>
          <input
            id="condition"
            type="text"
            className="input-large"
            value={condition}
            onChange={(event) => setCondition(event.target.value)}
          />
        </div>
        <button
          className="btn-primary"
          type="button"
          onClick={handleFindDoctors}
          disabled={!condition}
        >
          {labels['step.1.button']}
        </button>
      </div>
    )
  }

  function renderStepTwo() {
    return (
      <div className="step">
        <h2>{labels['step.2.title']}</h2>
        <div className="items-grid">
          {doctors.map((doctor) => (
            <div
              key={doctor.id || doctor.name}
              role="button"
              tabIndex={0}
              className={`item-card ${selectedDoctor === doctor ? 'selected' : ''}`}
              onClick={() => setSelectedDoctor(doctor)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setSelectedDoctor(doctor)
                }
              }}
            >
              <div className="item-info">
                <h3>{doctor.name}</h3>
                <p>
                  {doctor.hospital} • {doctor.specialty_tags}
                </p>
                <div className="signal-chips">
                  {doctor.match_score != null && (
                    <span className="signal-chip">
                      {labels['badge.score']}: {doctor.match_score}
                    </span>
                  )}
                  {doctor.tier && (
                    <span className="signal-chip muted">
                      {labels['badge.tier']}: {doctor.tier}
                    </span>
                  )}
                  {doctor.semantic_rank != null && (
                    <span className="signal-chip muted">
                      {labels['badge.semantic']}: #{doctor.semantic_rank}
                    </span>
                  )}
                </div>
                {doctor.reasoning && <div className="card-reasoning">{doctor.reasoning}</div>}
              </div>
              <button
                type="button"
                className="external-link"
                onClick={(event) => handleDoctorProfile(doctor, event)}
              >
                {labels['step.2.profile']}
              </button>
            </div>
          ))}
        </div>
        <button
          className="btn-primary"
          type="button"
          onClick={handleFindFlights}
          disabled={!selectedDoctor}
        >
          {labels['step.2.button']}
        </button>
        <button type="button" className="btn-secondary" onClick={() => setStep(2.5)}>
          {labels['step.2.refine']}
        </button>
      </div>
    )
  }

  function renderStepTwoPointFive() {
    return (
      <div className="step">
        <h2>{labels['step.2.5.title']}</h2>
        <div className="form-group">
          <label htmlFor="dissatisfaction">{labels['step.2.5.label']}</label>
          <input
            id="dissatisfaction"
            type="text"
            className="input-large"
            value={dissatisfactionReason}
            onChange={(event) => setDissatisfactionReason(event.target.value)}
            placeholder={labels['step.2.5.placeholder']}
          />
        </div>
        <button className="btn-primary" type="button" onClick={handleRefineDoctors}>
          {labels['step.2.5.button']}
        </button>
        <button type="button" className="btn-secondary" onClick={() => setStep(2)}>
          {labels['step.2.5.back']}
        </button>
      </div>
    )
  }

  function renderStepThree() {
    return (
      <div className="step">
        <h2>{labels['step.3.title']}</h2>
        <div className="items-grid">
          {flights.map((flight, flightIndex) => (
            <div
              key={flightIndex}
              role="button"
              tabIndex={0}
              className={`item-card ${selectedFlight === flight ? 'selected' : ''}`}
              onClick={() => setSelectedFlight(flight)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setSelectedFlight(flight)
                }
              }}
            >
              <div className="item-info">
                <h3>{flight.airline || flight.provider}</h3>
                <p>
                  {flight.route} • {flight.departure}
                </p>
                {flight.source && (
                  <div className="signal-chips">
                    <span className="signal-chip muted">
                      {labels['badge.source']}: {flight.source}
                    </span>
                  </div>
                )}
                <span className="price-tag">
                  {currency} {convertUsdPrice(flight.travel_cost_usd || flight.price || flight.fare)}
                </span>
                {flight.reasoning && <div className="card-reasoning">{flight.reasoning}</div>}
              </div>
            </div>
          ))}
        </div>
        <button
          className="btn-primary"
          type="button"
          onClick={handleFindCharities}
          disabled={!selectedFlight}
        >
          {labels['step.3.button']}
        </button>
      </div>
    )
  }

  function renderStepFour() {
    return (
      <div className="step">
        <h2>{labels['step.4.title']}</h2>
        <div className="items-grid">
          {charities.map((charity) => (
            <div
              key={charity.id || charity.name}
              role="button"
              tabIndex={0}
              className={`item-card ${selectedCharity === charity ? 'selected' : ''}`}
              onClick={() => setSelectedCharity(charity)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setSelectedCharity(charity)
                }
              }}
            >
              <div className="item-info">
                <h3>{charity.name}</h3>
                <span className="price-tag">
                  Up to {currency} {convertUsdPrice(charity.max_coverage_usd)}
                </span>
                {charity.website && charity.website !== '#' && (
                  <a
                    href={charity.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="external-link charity-link"
                    onClick={(event) => event.stopPropagation()}
                  >
                    Visit Website
                  </a>
                )}
                {charity.reasoning && <div className="card-reasoning">{charity.reasoning}</div>}
              </div>
            </div>
          ))}
          <div
            role="button"
            tabIndex={0}
            className={`item-card ${selectedCharity === 'NONE' ? 'selected' : ''}`}
            onClick={() => setSelectedCharity('NONE')}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                setSelectedCharity('NONE')
              }
            }}
          >
            <div className="item-info">
              <h3>Skip Financial Aid</h3>
              <p>I do not need charity assistance.</p>
            </div>
          </div>
        </div>
        <button
          className="btn-primary"
          type="button"
          onClick={generateSummary}
          disabled={!selectedCharity}
        >
          {labels['step.4.button']}
        </button>
      </div>
    )
  }

  function renderStepFive() {
    return (
      <div className="step">
        <h2>{labels['step.5.title']}</h2>

        <div className="items-grid review-grid">
          <div className="item-card selected">
            <div className="item-info">
              <h3>{selectedDoctor?.name}</h3>
              <p>{selectedDoctor?.hospital}</p>
            </div>
          </div>
          <div className="item-card selected">
            <div className="item-info">
              <h3>{selectedFlight?.airline}</h3>
              <p>{selectedFlight?.route}</p>
            </div>
          </div>
          {selectedCharity !== 'NONE' && selectedCharity && (
            <div className="item-card selected">
              <div className="item-info">
                <h3>{selectedCharity.name}</h3>
                <p>Financial Aid Selected</p>
              </div>
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="summary">{labels['step.5.summary_title']}</label>
          <div id="summary" className="summary-box">
            {summaryMessage}
          </div>
        </div>

        <div className="final-actions">
          <button
            className="btn-primary"
            type="button"
            onClick={() => handleGenerateLetter('visa_support')}
          >
            Download Visa Letter
          </button>
          <button
            className="btn-primary"
            type="button"
            onClick={() => handleGenerateLetter('hospital_letter')}
          >
            Download Hospital Letter
          </button>
          <button
            className="btn-primary"
            type="button"
            onClick={() => handleGenerateLetter('guidelines')}
          >
            Download Guidelines
          </button>
        </div>

        <div className="thinking-summary-step5">
          <h3 className="review-thinking-title">{labels['thinking.review_title']}</h3>
          <ReviewThinking labels={labels} transparency={transparencyByStep} />
        </div>
      </div>
    )
  }

  function renderCurrentStep() {
    if (step === 1) {
      return renderStepOne()
    }
    if (step === 2) {
      return renderStepTwo()
    }
    if (step === 2.5) {
      return renderStepTwoPointFive()
    }
    if (step === 3) {
      return renderStepThree()
    }
    if (step === 4) {
      return renderStepFour()
    }
    return renderStepFive()
  }

  return (
    <div className="app-container">
      <div className="brand-bar">
        <div className="brand-heading-row">
          <div className="logo-mark" aria-hidden="true">
            M
          </div>
          <div className="brand-text">
            <h1>{labels['app.title'] || 'Medical Match'}</h1>
            <p className="brand-tagline">{labels['app.tagline']}</p>
          </div>
        </div>

        <header>
          <div className="controls-row">
            <div className="form-group control-group">
              <label className="sr-only" htmlFor="currency-select">
                {labels['currency.select']}
              </label>
              <select
                id="currency-select"
                value={currency}
                onChange={(event) => setCurrency(event.target.value)}
                aria-label={labels['currency.select']}
              >
                {Object.keys(FALLBACK_RATES).map((rateCode) => (
                  <option key={rateCode} value={rateCode}>
                    {rateCode}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group control-group">
              <label className="sr-only" htmlFor="lang-select">
                Language
              </label>
              <select
                id="lang-select"
                value={language}
                onChange={handleLanguageChange}
                aria-label="Language"
              >
                {LANGUAGE_OPTIONS.map((languageOption) => (
                  <option key={languageOption.value} value={languageOption.value}>
                    {languageOption.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </header>
      </div>

      <Stepper labels={labels} currentStep={visibleStepperStep} />

      <div className="wizard-layout">
        <div className="wizard-main">
          <div className="wizard-card">
            {loading ? (
              <div className="loading-spinner">
                <div className="spinner" />
                <div>{labels['common.loading'] || 'Loading...'}</div>
              </div>
            ) : (
              renderCurrentStep()
            )}
          </div>
        </div>

        {!loading && step !== 5 && (
          <ThinkingPanel
            data={currentThinking}
            expanded={thinkingExpanded}
            onToggle={() => setThinkingExpanded((currentValue) => !currentValue)}
            labels={labels}
          />
        )}
      </div>
    </div>
  )
}

export default App
