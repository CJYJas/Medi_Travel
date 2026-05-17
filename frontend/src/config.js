export const RAW_API_BASE = import.meta.env.VITE_API_BASE

export const API_BASE =
  typeof RAW_API_BASE === 'string' && RAW_API_BASE.trim()
    ? RAW_API_BASE.trim().replace(/\/$/, '')
    : import.meta.env.DEV
      ? 'http://localhost:8000/api/v1'
      : '/api/v1'

export const FALLBACK_RATES = {
  USD: 1.0,
  MYR: 4.7,
  IDR: 15500.0,
  SGD: 1.35,
  THB: 36.5,
  VND: 24500.0,
  PHP: 56.0,
}

export const LANGUAGE_COUNTRY_MAP = {
  ms: 'Malaysia',
  id: 'Indonesia',
  th: 'Thailand',
  vi: 'Vietnam',
  fil: 'Philippines',
  km: 'Cambodia',
  lo: 'Laos',
  my: 'Myanmar',
}

export const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'ms', label: 'Bahasa Malaysia' },
  { value: 'id', label: 'Bahasa Indonesia' },
  { value: 'th', label: 'ไทย' },
  { value: 'vi', label: 'Tiếng Việt' },
  { value: 'fil', label: 'Filipino' },
  { value: 'km', label: 'ភាសាខ្មែរ' },
  { value: 'lo', label: 'ພາສາລາວ' },
  { value: 'my', label: 'မြန်မာဘာသာ' },
]

export const UI_STRINGS = {
  'app.title': 'Medical Matching Wizard',
  'app.tagline':
    'Structured matching across specialists, travel, and aid-transparent steps, not random suggestions.',
  'common.loading': 'Loading...',
  'stepper.1': 'Chart',
  'stepper.2': 'Specialist',
  'stepper.3': 'Travel',
  'stepper.4': 'Aid',
  'stepper.5': 'Review',
  'thinking.title': 'How the system decides',
  'thinking.show': 'Show details',
  'thinking.hide': 'Hide details',
  'thinking.signals': 'Signals from your case',
  'thinking.steps': 'What happens under the hood',
  'thinking.sources': 'Data sources',
  'thinking.review_title': 'Decision trail (this journey)',
  'thinking.none': 'Complete a step to see how that stage was decided.',
  'step.1.title': 'Step 1: Patient Information',
  'step.1.upload': 'Upload Medical Chart (PDF/Image)',
  'step.1.origin': 'Your Country',
  'step.1.condition': 'Medical Condition',
  'step.1.button': 'Find Specialists',
  'step.2.title': 'Step 2: Select a Doctor',
  'step.2.profile': 'View Profile',
  'step.2.button': 'Find Flights',
  'step.3.title': 'Step 3: Flight Options',
  'step.3.button': 'Find Financial Aid',
  'step.4.title': 'Step 4: Financial Aid / Charity',
  'step.4.button': 'Review Package',
  'step.5.title': 'Step 5: Final Review',
  'step.5.summary_title': 'Message for Hospital (Copy & Send):',
  'step.5.generate': 'Generate Visa/Support Letter',
  'currency.select': 'Currency:',
  'step.2.5.title': 'Help us refine your options',
  'step.2.5.label': 'Why are you dissatisfied?',
  'step.2.5.button': 'Search Again',
  'step.2.5.back': 'Back',
  'step.2.5.placeholder': 'e.g., Too expensive, prefer private hospital, etc.',
  'step.2.refine': 'Dissatisfied with these options?',
  'badge.score': 'Match score',
  'badge.tier': 'Tier',
  'badge.semantic': 'Search rank',
  'badge.source': 'Source',
}
