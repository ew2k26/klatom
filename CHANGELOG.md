# Changelog

## v4.0.0

### Changed
- Complete rebrand from KLATOM to ew²
- Ultra-dark visual theme across all interfaces
- Custom app icon integration
- Updated Discord support link
- Improved token flow and first-use experience
- Speed test now uses scraped proxy data directly
- Enhanced GUI with deeper dark palette

### Added
- App icon (.ico) support in build and window
- Multiple icon sizes for Windows compatibility

### Security
- Updated token prefix to EW2-
- Updated data directory to %LOCALAPPDATA%\ew2\
- SHA-256 checksum verification maintained

## v3.1.0

### Added
- Single executable distribution (onefile mode)
- Bundled fallback data for offline operation
- SHA-256 checksum verification
- Download website with security headers

### Changed
- Resources now load from bundled data when offline
- Improved error handling for network failures

### Security
- Encrypted auth storage with HMAC integrity
- HWID-bound trial sessions
- HTTPS-only network communications

## v2.1.1

- Initial test mode release
- Token management system
- Proxy speed testing

## v2.0.0

- Async checker engine
- Circuit breaker for proxy rotation
- Discord webhook integration

## v1.0.0

- Basic username checking functionality
