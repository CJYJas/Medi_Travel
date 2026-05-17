# Frontend

This folder contains the React + Vite user interface for the medical matching flow.

## Structure

```text
frontend/
|-- src/
|   |-- App.jsx              Workflow controller and API integration
|   |-- App.css              Main screen styling
|   |-- config.js            Shared UI strings, language options, API base config
|   |-- components/          Reusable presentational components
|   |-- assets/              Static frontend assets
|   `-- locales/             Locale JSON files
|-- public/                  Static public files
|-- package.json             Frontend scripts
`-- vite.config.js           Vite configuration
```

## Commands

From this folder:

```bash
npm install
npm run dev
```

Quality checks:

```bash
npm run build
npm run lint
```

## Notes

- `src/App.jsx` owns the step-by-step workflow state.
- `src/components/` is for reusable display components such as the stepper and transparency panel.
- Shared constants and environment-derived API configuration live in `src/config.js`.
