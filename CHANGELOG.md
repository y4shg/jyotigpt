# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-26

### Changed

- refactor: redefine dark/light mode color palettes via CSS custom properties in `app.css`
  - Light mode surfaces now use warm off-white tones (`#FFFFFF`, `#FAF8F3`, `#F5F2EB`)
  - Dark mode surfaces now use warm near-black tones (`#252523`, `#2E2E2C`, `#1E1D1C`)
- refactor: override primary action red palette with brand-aligned hues (`#E82020` light, `#F03030` dark)
- feat: apply Instrument Serif font to placeholder heading in `Placeholder.svelte`
- chore: extend `tailwind.config.js` with CSS variable-driven `red` palette alongside existing `gray` palette

## [1.0.8] - 2026-01-31

### Fixed

- fix: adjust stroke width for AdjustmentsHorizontal icon for better visibility
- refactor: update font styles for consistency across sidebar and chat components
- refactor: update external links and remove outdated references in various components
- chore: remove deprecated workflow files and add new disabled workflows for release, backend formatting, and frontend building
- fix: remove outdated favicon link from app.html
- Refactor code structure for improved readability and maintainability
- Refactor: Update references from JYOTIGPT to JyotiGPT across the codebase
- Updated comments, variable names, and strings to use "JyotiGPT" instead of "JYOTIGPT" for consistency.
- Modified Dockerfile, backend files, and frontend components to reflect the new naming convention.
- Incremented version numbers in package.json and package-lock.json to 1.0.7.
- Updated documentation and error messages to align with the new branding.

## [1.0.7] - 2026-01-28

### Fixed

- Refactor: Update references from JYOTIGPT to JyotiGPT across the codebase
- Updated comments, variable names, and strings to use "JyotiGPT" instead of "JYOTIGPT" for consistency.
- Modified Dockerfile, backend files, and frontend components to reflect the new naming convention.
- Incremented version numbers in package.json and package-lock.json to 1.0.7.
- Updated documentation and error messages to align with the new branding.

## [1.0.6] - 2026-01-27

### Added

- Refactor Navbar components to use SidebarIcon and remove MenuLines; add SidebarIcon component

## [1.0.5] - 2026-01-26

### Added

- Remove unnecessary padding from Placeholder and adjust Sidebar class for cleaner layout

## [1.0.4] - 2026-01-26

### Added

- remap sidebar fixes

## [1.0.3] - 2026-01-26

### Added

- remap sidebar :)

## [1.0.2] - 2026-01-26

### Added

- refactor ascii art

## [1.0.1] - 2026-01-26

### Added

- new skeleton.

## [1.0.0] - 2026-01-25

### update

- opened repo, renamed.
