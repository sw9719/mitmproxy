#!/usr/bin/env python3
import os
import shutil
from pathlib import Path

import pdoc.render

here = Path(__file__).parent

if os.environ.get("DOCS_ARCHIVE", False):
    edit_url_map = {}
else:
    edit_url_map = {
        "mitmproxy": "https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/",
    }

pdoc.render.configure(
    template_directory=here / "pdoc-template",
    edit_url_map=edit_url_map,
)

modules = [
    "mitmproxy.proxy.context",
    "mitmproxy.http",
    "mitmproxy.flow",
    "mitmproxy.tcp",
    "mitmproxy.websocket",
]

pdoc.pdoc(
    *modules,
    output_directory=here / ".." / "src" / "generated" / "api"
)

api_content = here / ".." / "src" / "content" / "api"
if api_content.exists():
    shutil.rmtree(api_content)

api_content.mkdir()

for module in modules:
    filename = f"api/{ module.replace('.','/') }.html"
    (api_content / f"{module}.md").write_text(f"""
---
title: "{module}"
url: "{filename}"

menu:
    addons:
        parent: 'API Reference'
---

{{{{< readfile file="/generated/{filename}" >}}}}
""")

(api_content / f"_index.md").write_text(f"""
---
title: "API Reference"
layout: single
menu:
    addons:
        weight: 5
---

# API Reference
""")
