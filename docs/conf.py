project = "NexusTrader MCP"
author = "QuantWeb3"
copyright = "2026, QuantWeb3"
release = "0.1.1"

extensions = [
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"
language = "zh_CN"
html_theme = "furo"
html_title = "NexusTrader MCP Docs"
html_static_path = ["_static"]
html_theme_options = {
    "sidebar_hide_name": False,
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
