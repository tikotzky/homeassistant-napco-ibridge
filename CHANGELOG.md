# Changelog

## [0.1.1](https://github.com/tikotzky/homeassistant-napco-ibridge/compare/v0.1.0...v0.1.1) (2026-05-14)


### Features

* add send_code service and conditional arm/disarm buttons ([f91b8ac](https://github.com/tikotzky/homeassistant-napco-ibridge/commit/f91b8ac4854af1e757a3abd91d3cff6b61bc3b88))
* **api:** port Napco iBridge TCP/UDP protocol to async Python client ([6c3a0d9](https://github.com/tikotzky/homeassistant-napco-ibridge/commit/6c3a0d91a1fd9b63142f9d2178d4ffa3dfd8574a))
* **config_flow:** drop save-code toggle; optional code field decides behavior ([3d19f66](https://github.com/tikotzky/homeassistant-napco-ibridge/commit/3d19f6612d1348163b251dab3875a7af2be6e56b))
* implement coordinator, config flow, platforms, and send_keys service ([cf61a64](https://github.com/tikotzky/homeassistant-napco-ibridge/commit/cf61a643d7db17daa8f777cb19951f7790c43c8c))
* serve brand images from the integration directory ([6a1bf0f](https://github.com/tikotzky/homeassistant-napco-ibridge/commit/6a1bf0fe719327fdfb424f308e8872e6424a6dfc))


### Bug Fixes

* **arm:** match Napco's actual long-press arm sequences ([17f81f0](https://github.com/tikotzky/homeassistant-napco-ibridge/commit/17f81f04e642ff6840614f334405e6682eb3c0a8))
* **brand:** regenerate logo.png as square to avoid stretching ([6d95c55](https://github.com/tikotzky/homeassistant-napco-ibridge/commit/6d95c557ddd441c9e8fa6ea385b3557c1cee819c))
* **send_keys:** allow duplicate buttons in the keys selector ([bcd232e](https://github.com/tikotzky/homeassistant-napco-ibridge/commit/bcd232e43995e13b85b84ff78b282a268ce995c8))
