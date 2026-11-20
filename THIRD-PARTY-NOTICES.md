# Third-party notices

FFR Trainer itself is licensed under the GNU General Public License v3.0 (see `LICENSE`).

The distributable build (`FFR-Trainer.exe` and the `_internal` folder) bundles the third-party
components listed below. Each remains under its own license; the list is provided for attribution.
It was generated from the package metadata of the build environment and has not been legally reviewed.

## Runtime and platform components

| Component | License | Source |
|---|---|---|
| Python 3.14.7 runtime and standard library | PSF-2.0 | https://www.python.org/ |
| Flet desktop client (`flet.exe`, bundled as `flet-windows.zip`) | Apache-2.0 | https://github.com/flet-dev/flet |
| Flutter engine and framework (inside the Flet client) | BSD-3-Clause | https://github.com/flutter/flutter |
| PyInstaller bootloader | GPL-2.0-or-later with a special exception that permits distributing bundled applications under any license | https://github.com/pyinstaller/pyinstaller |
| OpenSSL (`libcrypto-3.dll`, `libssl-3.dll`) | Apache-2.0 | https://www.openssl.org/ |
| libffi (`libffi-8.dll`) | MIT | https://github.com/libffi/libffi |
| Microsoft Visual C++ runtime (`VCRUNTIME140*.dll`) | Microsoft redistributable terms | https://visualstudio.microsoft.com/license-terms/ |

The Flet desktop client carries the license notices of Flutter and of the Flutter packages it uses
inside its own application data.

## Python packages

| Package | Version | License | Source |
|---|---|---|---|
| annotated-doc | 0.0.7 | MIT | https://github.com/fastapi/annotated-doc |
| annotated-types | 0.8.0 | MIT | https://github.com/annotated-types/annotated-types |
| anyio | 4.16.0 | MIT | https://github.com/agronholm/anyio |
| certifi | 2026.10.23 | MPL-2.0 | https://github.com/certifi/python-certifi |
| chardet | 5.2.0 | LGPL-2.1-or-later | https://github.com/chardet/chardet |
| click | 8.5.1 | BSD-3-Clause | https://github.com/pallets/click/ |
| fastapi | 0.165.0 | MIT | https://github.com/fastapi/fastapi |
| flet | 1.1.2 | Apache-2.0 | https://flet.dev |
| flet-cli | 1.1.2 | Apache-2.0 | https://flet.dev |
| flet-desktop | 1.1.2 | Apache-2.0 | https://flet.dev |
| flet-web | 1.1.2 | Apache-2.0 | https://flet.dev |
| h11 | 0.16.0 | MIT | https://github.com/python-hyper/h11 |
| httpcore | 1.0.9 | BSD-3-Clause | https://www.encode.io/httpcore/ |
| httptools | 0.9.0 | MIT | https://github.com/MagicStack/httptools |
| httpx | 0.28.1 | BSD-3-Clause | https://github.com/encode/httpx |
| idna | 3.20 | BSD-3-Clause | https://github.com/kjd/idna |
| markdown-it-py | 4.3.0 | MIT | https://github.com/executablebooks/markdown-it-py |
| mdurl | 0.1.2 | MIT | https://github.com/executablebooks/mdurl |
| msgpack | 1.2.4 | Apache-2.0 | https://msgpack.org/ |
| oauthlib | 4.0.1 | BSD-3-Clause | https://github.com/oauthlib/oauthlib |
| opentelemetry-api | 1.45.2 | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-api |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | https://github.com/pypa/packaging |
| pillow | 13.0.0 | MIT-CMU | https://python-pillow.org |
| pydantic | 2.14.4 | MIT | https://github.com/pydantic/pydantic |
| pydantic_core | 2.50.5 | MIT | https://github.com/pydantic/pydantic |
| Pygments | 2.21.0 | BSD-2-Clause | https://pygments.org |
| python-dotenv | 1.2.4 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| PyYAML | 6.0.3 | MIT | https://pyyaml.org/ |
| repath | 0.9.0 | MIT | https://github.com/nickcoutsos/python-repath |
| rich | 15.0.0 | MIT | https://github.com/Textualize/rich |
| setuptools | 84.2.1 | MIT | https://github.com/pypa/setuptools |
| six | 1.17.0 | MIT | https://github.com/benjaminp/six |
| starlette | 1.10.0 | BSD-3-Clause | https://github.com/Kludex/starlette |
| typing-inspection | 0.4.5 | MIT | https://github.com/pydantic/typing-inspection |
| typing_extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| tzdata | 2026.6 | Apache-2.0 | https://github.com/python/tzdata |
| uvicorn | 0.54.0 | BSD-3-Clause | https://uvicorn.dev/ |
| watchfiles | 1.3.0 | MIT | https://github.com/samuelcolvin/watchfiles |
| websockets | 17.4 | BSD-3-Clause | https://github.com/python-websockets/websockets |

License texts for these packages are available from the linked project pages. Where a package ships a
license file in its distribution metadata, that file is included under `_internal/<package>.dist-info/licenses/`.
